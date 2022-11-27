#!/usr/bin/env python

import asyncio
import json
import signal
import sys
import websockets
import weechat



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
    if message[0] == "EVENT":
        ty, subscription_id, event = message
        content = event["content"]
        print(short_id(event["id"]), content)
    else:
        print("Unknown message type", message[0])


# callback for data received in input
def buffer_input_cb(data, buffer, input_data):
    weechat.prnt("", f"buffer is {buffer}")
    weechat.prnt(weechat.current_buffer(), "Cannot send messages yet. Sorry!")
    return weechat.WEECHAT_RC_OK

# callback called when buffer is closed
def buffer_close_cb(data, buffer):
    weechat.prnt(weechat.current_buffer(), "Goodbye.")
    return weechat.WEECHAT_RC_OK


weechat.register("nostr", "Max B", "0.0", "MIT", "Use weechat as a nostr client", "", "")
buffer = weechat.buffer_new("nostr", "buffer_input_cb", "", "buffer_close_cb", "")
weechat.buffer_set(buffer, "title", "nostr buffer")


async def main():
    server = SERVER
    async with websockets.connect(server) as websocket:
        # Close the connection when receiving SIGTERM.
        # loop = asyncio.get_running_loop()
        # loop.add_signal_handler(signal.SIGTERM, loop.create_task, websocket.close())

        await websocket.send(
            make_request(SUBSCRIPTION_ID, {"limit": 100, "since": 1669524090})
        )
        await asyncio.sleep(0)  # yield control to the event loop
        async for message in websocket:
            weechat.prnt(buffer, message)
            await asyncio.sleep(0)  # yield control to the event loop
            # display_message(json.loads(message))

asyncio.run(main())
