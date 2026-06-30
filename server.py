import asyncio
import json
import websockets

async def handler(websocket: websockets):
    try:
        async for message in websocket:
            msg = json.loads(message)
            intent = {"mx" : 0,
                      "my" : -1,
                      "fire" : False,
                      "aim_x": 0,
                      "aim_y" : 0
                      }
            await websocket.send(json.dumps(intent))

    except websockets.ConnectionClosed:
        print("Client disconnected normally.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()

async def main():
    async with websockets.serve(handler, "0.0.0.0", 5884):
        print("WebSocket Server started on ws://0.0.0.0:5884")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())