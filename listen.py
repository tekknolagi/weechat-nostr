#!/usr/bin/env python

import asyncio
import json
import signal
import sys
import websockets


SUBSCRIPTION_ID = "maxmaxmax"
SERVER = "wss://nostr-pub.wellorder.net"


def slim_json_dump(obj):
    return json.dumps(obj, separators=(",", ":"))


def make_request(subscription_id, filters_json=None):
    return slim_json_dump(["REQ", subscription_id, filters_json or {}])


def short_id(id):
    return id[:4] + "..." + id[-4:]


def display_message(message):
    ty = message[0]
    if ty == "NOTICE":
        print(*message)
        return
    ty, subscription_id, event = message
    content = event["content"]
    print(short_id(event["id"]), content)


async def run_client(server):
    async with websockets.connect(server) as websocket:
        # Close the connection when receiving SIGTERM.
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, loop.create_task, websocket.close())

        await websocket.send(
            make_request(SUBSCRIPTION_ID, {"limit": 100, "since": 1669524090})
        )
        async for message in websocket:
            display_message(json.loads(message))


server = sys.argv[1]

try:
    asyncio.run(run_client(server))
except KeyboardInterrupt:
    print("Goodbye.")
