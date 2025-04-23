import asyncio
import websockets
import json
import random
import os

players = {}
connections = set()
apple = {"x": 300, "y": 300}

async def handler(ws):
    player_id = str(id(ws))
    players[player_id] = {
        "x": 100, "y": 100,
        "length": 1, "trail": [], "color": "lime",
        "dir": "right", "name": f"Player-{player_id[-4:]}"
    }
    connections.add(ws)

    try:
        async for msg in ws:
            data = json.loads(msg)
            if "color" in data:
                players[player_id]["color"] = data["color"]
            if "name" in data:
                players[player_id]["name"] = data["name"]
            if "dir" in data:
                players[player_id]["dir"] = data["dir"]
    finally:
        connections.remove(ws)
        del players[player_id]

async def broadcast_loop():
    while True:
        for pid in players:
            direction = players[pid]["dir"]
            if direction == "up": players[pid]["y"] -= 10
            elif direction == "down": players[pid]["y"] += 10
            elif direction == "left": players[pid]["x"] -= 10
            elif direction == "right": players[pid]["x"] += 10

            players[pid]["x"] = max(0, min(590, players[pid]["x"]))
            players[pid]["y"] = max(0, min(590, players[pid]["y"]))

            if abs(players[pid]["x"] - apple["x"]) < 20 and abs(players[pid]["y"] - apple["y"]) < 20:
                players[pid]["length"] += 1
                apple["x"] = random.randint(50, 550)
                apple["y"] = random.randint(50, 550)

        if connections:
            data = json.dumps({"players": players, "apple": apple})
            await asyncio.gather(*[ws.send(data) for ws in connections])
        await asyncio.sleep(0.1)

async def main():
    port = int(os.environ.get("PORT", 6789))  # Render sets PORT
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"WebSocket server running on port {port}")
        await broadcast_loop()

asyncio.run(main())