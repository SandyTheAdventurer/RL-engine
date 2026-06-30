import asyncio
import json
import websockets

connections: dict[int, websockets.WebSocketServerProtocol] = {}
next_id = 0


def compute_intent(observation: dict, player_id: int) -> dict:
    """Placeholder — replace with actual RL model inference."""
    if player_id == 1:
        return {
            "type": "intent",
            "mx": 0,
            "my": -1,
            "fire": False,
            "aim_x": 540.0,
            "aim_y": 360.0,
        }
    return {
        "type": "intent",
        "mx": 0,
        "my": 1,
        "fire": False,
        "aim_x": 540.0,
        "aim_y": 360.0,
    }


async def handler(websocket: websockets.WebSocketServerProtocol):
    global next_id
    player_id = next_id
    next_id += 1
    connections[player_id] = websocket
    print(f"Player {player_id} connected ({len(connections)} total)")

    config = {"type": "config", "data_iter": 5, "train_iter": 100}
    await websocket.send(json.dumps(config))

    try:
        async for message in websocket:
            msg = json.loads(message)
            game_state = msg.get("game_state", "")

            if game_state == "TRAINING":
                print(f"Training observation from player {player_id}")

            if game_state == "PLAYING" and "expert_action" in msg:
                with open("bc_data.jsonl", "a") as f:
                    f.write(json.dumps(msg) + "\n")

            intent = compute_intent(msg, player_id)
            intent["player_id"] = player_id
            await websocket.send(json.dumps(intent))

    except websockets.ConnectionClosed:
        print(f"Player {player_id} disconnected")
    except Exception as e:
        print(f"Player {player_id} error: {e}")
    finally:
        connections.pop(player_id, None)


async def main():
    async with websockets.serve(handler, "0.0.0.0", 5884):
        print("Server ready on ws://0.0.0.0:5884")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
