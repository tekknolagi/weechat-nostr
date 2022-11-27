#!/usr/bin/env python

import asyncio
import hashlib
import json
import sys
import time
import websockets
from secp256k1 import PrivateKey, PublicKey

PRIVKEY = PrivateKey(b"x" * 32)
PUBKEY = PRIVKEY.pubkey

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
    return hashlib.sha256(serialized_utf8).hexdigest()


def sign(obj):
    assert isinstance(obj, str)
    raw_sig = PRIVKEY.ecdsa_sign(obj.encode("utf-8"))
    return PRIVKEY.ecdsa_serialize(raw_sig).hex()


def make_request(subscription_id, filters_json=None):
    return slim_json_dump(["REQ", subscription_id, filters_json or {}])


def display_message(message):
    ty = message[0]
    if ty == "NOTICE":
        print(*message)
        return
    ty, subscription_id, event = message
    content = event["content"]
    print(short_id(event["id"]), content)


def make_event(content):
    pubkey = PUBKEY.serialize().hex()
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
    print('SERIALIZED',serialized)
    event_id = hash_json_of(serialized)
    sig = sign(event_id)
    return {
        "id": event_id,
        "pubkey": pubkey,
        "created_at": created_at,
        "kind": kind,
        "tags": tags,
        "content": content,
        "sig": sig,
    }


def make_event_message(event):
    print("EVENT",event)
    return slim_json_dump(["EVENT", event])


async def run_client(server):
    async with websockets.connect(server) as websocket:
        event = make_event_message(make_event("hello world"))
        print("Sending", event)
        await websocket.send(event)

        response = await websocket.recv()
        print(response)
        try:
            message = json.loads(response)
            display_message(message)
        except json.decoder.JSONDecodeError:
            print("Server sent bad response", response)


server = sys.argv[1]
try:
    asyncio.run(run_client(server))
except KeyboardInterrupt:
    print("Goodbye.")
