#!/usr/bin/env python3
"""
Quick WebSocket test client to verify the Django Channels backend
"""
import asyncio
import websockets
import json


async def test_websocket():
    uri = "ws://localhost:8000/ws/checkins/"

    print(f"Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✓ Connected successfully!")

            # Wait for the connection_established message
            response = await websocket.recv()
            data = json.loads(response)
            print(f"✓ Received: {data}")

            if data.get('type') == 'connection_established':
                print("✓ Connection established message received")

            # Keep connection open for a bit
            print("\nWaiting for messages (5 seconds)...")
            try:
                await asyncio.wait_for(websocket.recv(), timeout=5.0)
            except asyncio.TimeoutError:
                print("✓ No messages received (expected for idle connection)")

            print("\n✓ WebSocket test PASSED - connection works!")

    except Exception as e:
        print(f"✗ WebSocket test FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_websocket())
