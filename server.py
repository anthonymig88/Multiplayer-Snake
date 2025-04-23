import asyncio
import websockets
import json
import random
import os
from aiohttp import web

players = {}
connections = set()
apple = {"x": 300, "y": 300}

def clamp(val, minv, maxv):
    return max(minv, min(maxv, val))

async def handler(ws):
    player_id = str(id(ws))
    players[player_id] = {
        "x": 100, "y": 100,
        "length": 5,
        "trail": [[100, 100]] * 5,
        "color": "lime",
        "dir": "right",
        "name": f"Player-{player_id[-4:]}"
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
        growth_messages = []
        for pid, p in players.items():
            dx, dy = 0, 0
            if p["dir"] == "up": dy = -10
            elif p["dir"] == "down": dy = 10
            elif p["dir"] == "left": dx = -10
            elif p["dir"] == "right": dx = 10

            new_x = clamp(p["x"] + dx, 0, 590)
            new_y = clamp(p["y"] + dy, 0, 590)
            p["x"], p["y"] = new_x, new_y
            p["trail"].insert(0, [new_x, new_y])
            if len(p["trail"]) > p["length"]:
                p["trail"].pop()

            if abs(new_x - apple["x"]) < 10 and abs(new_y - apple["y"]) < 10:
                p["length"] += 1
                apple["x"] = random.randint(0, 59) * 10
                apple["y"] = random.randint(0, 59) * 10
                growth_messages.append(f"+1 {p['name']}")

        data = json.dumps({"players": players, "apple": apple, "growth": growth_messages})
        await asyncio.gather(*[ws.send(data) for ws in connections])
        await asyncio.sleep(0.1)

async def health_check(request):
    return web.Response(text="OK")

async def start_http_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()

async def main():
    port = int(os.environ.get("PORT", 6789))
    await start_http_server()
    async with websockets.serve(handler, "0.0.0.0", port):
        print(f"WebSocket server running on port {port}")
        await broadcast_loop()

asyncio.run(main())