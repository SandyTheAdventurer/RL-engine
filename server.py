import asyncio
import json
import logging as log
import os
import pathlib
import websockets
import torch

from rl.bc import BC
from rl.ppo import PPO, PPOBuffer, PPORolloutWorker
from rl.utils import flatten_obs, to_tensor, format_intent

log.basicConfig(level=log.INFO)

HERE = os.path.dirname(os.path.abspath(__file__))
BC_MODEL_PATH = os.path.join(HERE, "rl", "bc.pt")
DATA_PATH = os.path.join(HERE, "bc_data.jsonl")
INPUT_DIM = 68

bc_config = {
    "input_dim": INPUT_DIM,
    "hidden_dim": 256,
    "n_layers": 4,
    "batch_size": 64,
    "lr": 1e-3,
    "screenw": 1080,
    "screenh": 720,
    "activation": "relu",
}

ppo_config = {
    "input_dim": INPUT_DIM,
    "hidden_dim": 512,
    "n_layers": 4,
    "batch_size": 64,
    "lr": 3e-4,
    "screenw": 1080,
    "screenh": 720,
    "activation": "relu",
    "gamma": 0.99,
    "lam": 0.95,
    "clip_epsilon": 0.2,
    "n_epochs": 10,
    "entropy_coef": 0.01,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
}

train_lock = asyncio.Lock()
connections = set()

bc_trained = False
bc_model = None
ppo_agent = PPO(ppo_config, "cuda")
ppo_worker = PPORolloutWorker(ppo_agent, PPOBuffer())

async def run_bc_training():
    """Encapsulates BC training logic"""
    global bc_trained, bc_model
    bc_path = pathlib.Path(DATA_PATH)
    if not bc_path.exists():
        log.info("bc_data.jsonl not found, skipping BC.")
        return

    log.info("Starting BC processing...")
    clone = BC(bc_config, "cuda")
    await asyncio.to_thread(clone.preprocess, DATA_PATH)
    await asyncio.to_thread(clone.learn, n_epochs=10)
    clone.save(BC_MODEL_PATH)
    bc_model = clone
    bc_trained = True
    
    # Ensure PPO starts with a clean slate after BC finishes
    ppo_worker.reset_step_state() 
    log.info("BC training complete.")

async def handler(websocket: websockets.WebSocketServerProtocol):
    global bc_trained, ppo_worker

    connections.add(websocket)
    log.info(f"Client connected ({len(connections)} total)")

    await websocket.send(json.dumps({"type": "config", "data_iter": 5, "train_iter": 10}))

    try:
        async for message in websocket:
            msg = json.loads(message)
            game_state = msg.get("game_state", "")

            # 1. Behavioral Cloning Boot-up (Runs once)
            if game_state == "TRAINING" and not bc_trained:
                async with train_lock:
                    if not bc_trained:
                        await run_bc_training()
                        
            # 2. Data Collection
            elif game_state == "PLAYING" and "expert_action" in msg:
                bc_trained = False
                with open(DATA_PATH, "a") as f:
                    f.write(json.dumps(msg) + "\n")

            # 3. Action Pipeline
            if "self" not in msg:
                continue

            role = msg.get("role", "agent")
            obs_t = to_tensor(flatten_obs(msg["self"]), ppo_agent.device)

            if role == "clone" and game_state == "TRAINING" and bc_model is not None:
                mx, my, fire, aim_x, aim_y = bc_model.sample(obs_t)
                intent = {
                    "type": "intent",
                    "mx": [-1, 0, 1][mx],
                    "my": [-1, 0, 1][my],
                    "fire": fire,
                    "aim_x": aim_x,
                    "aim_y": aim_y,
                }
            else:
                mx, my, fire, aim = ppo_worker.step(
                    obs_t, msg["self"]["health"], msg["self"]["enemy_health"]
                )
                intent = format_intent(mx, my, fire, aim)

            await websocket.send(json.dumps(intent))

    except websockets.ConnectionClosed as e:
        log.info(f"Client disconnected: code={e.code}")
    except Exception as e:
        log.exception("Handler error")
        os._exit(1)
    finally:
        connections.discard(websocket)

async def main():
    async with websockets.serve(handler, "0.0.0.0", 5884, ping_timeout=None):
        log.info("Server ready on ws://0.0.0.0:5884")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())