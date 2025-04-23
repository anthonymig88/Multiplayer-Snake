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
        "length": 1,
        "trail": [[100, 100]] * 1,
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
        remove_players = []

        all_trails = []
        for pid, p in players.items():
            # Skip head but collect all trail blocks
            if len(p["trail"]) > 1:
                all_trails.extend(p["trail"][1:] + [["owner", pid]])

        for pid, p in list(players.items()):
            dx, dy = 0, 0
            if p["dir"] == "up": dy = -10
            elif p["dir"] == "down": dy = 10
            elif p["dir"] == "left": dx = -10
            elif p["dir"] == "right": dx = 10

            new_x = p["x"] + dx
            new_y = p["y"] + dy

            # Wall collision detection
            if new_x < 0 or new_x > 590 or new_y < 0 or new_y > 590:
                remove_players.append(pid)
                continue

            # Collision with self or others
            for tid, t in players.items():
                for i, segment in enumerate(t["trail"]):
                    # Skip checking head-to-head collisions
                    if tid == pid and i == 0:
                        continue
                    if segment[0] == new_x and segment[1] == new_y:
                        remove_players.append(pid)
                        break
                if pid in remove_players:
                    break

            if pid in remove_players:
                continue

            p["x"], p["y"] = new_x, new_y
            p["trail"].insert(0, [new_x, new_y])
            if len(p["trail"]) > p["length"]:
                p["trail"].pop()

            if abs(new_x - apple["x"]) < 10 and abs(new_y - apple["y"]) < 10:
                p["length"] += 1
                apple["x"] = random.randint(0, 59) * 10
                apple["y"] = random.randint(0, 59) * 10
                growth_messages.append(f"+1 {p['name']}")

        for pid in remove_players:
            if pid in players:
                del players[pid]

        data = json.dumps({"players": players, "apple": apple, "growth": growth_messages, "dead": remove_players})
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