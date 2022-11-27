#!/usr/bin/env python

import asyncio
import hashlib
import json
import signal
import sys
import time
import websockets
from bip340 import pubkey_gen as PublicKey, schnorr_sign


def PrivateKey(x):
    return x


PRIVKEY = PrivateKey(b"x" * 32)
PUBKEY = PublicKey(PRIVKEY)

# import sys;sys.exit(0)

SUBSCRIPTION_ID = "maxmaxmax"
SERVER = "wss://nostr-pub.wellorder.net"


class EventKind:
    set_metadata = 0
    text_note = 1
    recommend_server = 2


def slim_json_dump(obj):
    return json.dumps(obj, separators=(",", ":"))


def hash_json_of(obj):
    serialized_utf8 = slim_json_dump(obj).encode("utf-8")
    return hashlib.sha256(serialized_utf8).digest()


def sign(obj):
    assert isinstance(obj, bytes)
    raw_sig = schnorr_sign(obj, PRIVKEY, aux_rand=b"x" * 32)
    return raw_sig.hex()


def make_request(subscription_id, filters_json=None):
    return slim_json_dump(["REQ", subscription_id, filters_json or {}])


def make_event(content):
    pubkey = PUBKEY.hex()
    created_at = int(time.time())
    kind = EventKind.text_note
    tags = []
    assert isinstance(content, str)
    assert all(isinstance(tag, str) for tag in tags)
    serialized = [
        0,
        pubkey,
        created_at,
        kind,
        tags,
        content,
    ]
    event_id = hash_json_of(serialized)
    sig = sign(event_id)
    return {
        "id": event_id.hex(),
        "pubkey": pubkey,
        "created_at": created_at,
        "kind": kind,
        "tags": tags,
        "content": content,
        "sig": sig,
    }


def make_event_message(event):
    return slim_json_dump(["EVENT", event])


async def run_client(server, msg):
    async with websockets.connect(server) as websocket:
        # Close the connection when receiving SIGTERM.
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, loop.create_task, websocket.close())

        event = make_event_message(make_event(msg))
        await websocket.send(event)

        response = await websocket.recv()
        print(response)


server = sys.argv[1]
msg = sys.argv[2]

try:
    asyncio.run(run_client(server, msg))
except KeyboardInterrupt:
    print("Goodbye.")
