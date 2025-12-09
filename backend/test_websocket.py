#!/usr/bin/env python
"""
Simple WebSocket connection test for Django Channels
"""
import asyncio
import websockets
import json


async def test_websocket():
    uri = "ws://localhost:8000/ws/checkins/"

    try:
        async with websockets.connect(uri) as websocket:
            print(f"✓ Connected to {uri}")

            # Wait for connection confirmation
            message = await websocket.recv()
            data = json.loads(message)
            print(f"✓ Received: {data}")

            if data.get("type") == "connection_established":
                print("✓ WebSocket connection test PASSED")
                return True
            else:
                print(f"✗ Unexpected message type: {data.get('type')}")
                return False

    except Exception as e:
        print(f"✗ WebSocket connection test FAILED: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_websocket())
    exit(0 if result else 1)
