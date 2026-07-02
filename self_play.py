import logging
import sys
import os
import time
sys.path.append(os.path.abspath("./build"))

import torch

from Game import Engine, Player, PlayerIntent, poll_events
from rl.ppo import PPO, PPORolloutWorker
from rl.utils import to_tensor

log = logging.getLogger(__name__)

system_config = {
    "screenw": 1080,
    "screenh": 720,
    "is_render": True,
    "is_server": True,
    "target_fps": 60,
    "max_dt": 1 / 30,
    "player_speed": 200.0,
    "max_health": 1000,
    "input_dim": 70,
    "dt": 1 / 60,
    "p1_start_x": 240.0,
    "p1_start_y": 285.0,
    "p2_start_x": 390.0,
    "p2_start_y": 285.0,
    "update_interval": 500,
    "checkpoint_path": "rl/ppo_selfplay.pt",
    "checkpoint_every": 20,
    "snapshot_every": 50,
    "max_episodes": -1,
}

ppo_config = {
    "input_dim": system_config["input_dim"],
    "hidden_dim": 512,
    "n_layers": 4,
    "batch_size": 64,
    "lr": 3e-4,
    "screenw": system_config["screenw"],
    "screenh": system_config["screenh"],
    "activation": "relu",
    "gamma": 0.99,
    "lam": 0.95,
    "clip_epsilon": 0.2,
    "n_epochs": 10,
    "entropy_coef": 0.01,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
}


def make_intent(mx, my, fire, aim, screenw, screenh):
    mx = int(mx.item()) - 1
    my = int(my.item()) - 1
    fire = bool(fire.item())
    aim_x = (aim[0, 0].item() + 1) / 2 * screenw
    aim_y = (aim[0, 1].item() + 1) / 2 * screenh
    return PlayerIntent(mx, my, fire, aim_x, aim_y)


def compute_dt(cfg, last_time):
    if not cfg["is_render"]:
        return cfg["dt"]
    now = time.perf_counter()
    dt = now - last_time
    return min(dt, cfg["max_dt"])


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info("Using device: %s", device)

    cfg = system_config

    p1 = Player(cfg["p1_start_x"], cfg["p1_start_y"], cfg["player_speed"], "agent")
    p2 = Player(cfg["p2_start_x"], cfg["p2_start_y"], cfg["player_speed"], "opponent")

    engine = Engine(cfg["is_render"], cfg["is_server"], p1, p2, cfg["screenw"], cfg["screenh"])

    agent = PPO(ppo_config, device)
    opponent = PPO(ppo_config, device)
    opponent.load_state_dict(agent.state_dict())
    opponent.eval()

    if os.path.exists(cfg["checkpoint_path"]):
        agent.load(cfg["checkpoint_path"])
        opponent.load_state_dict(agent.state_dict())
        log.info("Resumed from %s (update #%d)", cfg["checkpoint_path"], agent.update_counter)

    worker = PPORolloutWorker(agent, update_interval=cfg["update_interval"])
    last_snapshot = agent.update_counter

    running = True
    episode = 0

    try:
        while running:
            engine.reset()
            episode += 1

            obs = to_tensor(engine.observe(p1, p2), device)
            opponent_obs = to_tensor(engine.observe(p2, p1), device)

            last_time = time.perf_counter()

            while not engine.is_done():
                if cfg["is_render"]:
                    frame = poll_events()
                    if frame.quit:
                        running = False
                        break

                mx, my, fire, aim = worker.step(obs, p1.health, p2.health)
                p1_intent = make_intent(mx, my, fire, aim, cfg["screenw"], cfg["screenh"])

                opp_mx, opp_my, opp_fire, opp_aim, _, _ = opponent.get_action(opponent_obs)
                p2_intent = make_intent(opp_mx, opp_my, opp_fire, opp_aim, cfg["screenw"], cfg["screenh"])

                dt = compute_dt(cfg, last_time)
                engine.step(p1_intent, p2_intent, dt)
                last_time = time.perf_counter()

                if cfg["is_render"]:
                    engine.render()
                    engine.present()

                obs = to_tensor(engine.observe(p1, p2), device)
                opponent_obs = to_tensor(engine.observe(p2, p1), device)

            if not running:
                break

            if cfg["max_episodes"] != -1 and episode >= cfg["max_episodes"]:
                log.info("Reached max_episodes=%d, stopping", cfg["max_episodes"])
                break

            if episode % 100 == 0:
                log.info("Episode %d", episode)

            stats = worker.maybe_update()
            if stats is not None:
                agent.save(cfg["checkpoint_path"])
                log.info("Checkpoint saved (update #%d)", agent.update_counter)

                if agent.update_counter - last_snapshot >= cfg["snapshot_every"]:
                    opponent.load_state_dict(agent.state_dict())
                    opponent.eval()
                    last_snapshot = agent.update_counter
                    log.info("Opponent snapshot refreshed (update #%d)", agent.update_counter)

    except KeyboardInterrupt:
        log.info("Interrupted")
    finally:
        engine.close()


if __name__ == "__main__":
    main()
