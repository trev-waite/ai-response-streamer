import asyncio
import websockets

async def test_websocket():
    uri = "ws://localhost:8765"
    
    async with websockets.connect(uri) as websocket:
        # Send a test prompt
        prompt = "Tell me a short story about a cat."
        await websocket.send(prompt)
        print(f"Sent prompt: {prompt}")
        
        # Receive and print the streamed response
        print("Response:")
        while True:
            try:
                chunk = await websocket.recv()
                print(chunk, end="", flush=True)  # Print each chunk as it arrives
            except websockets.ConnectionClosed:
                print("\nConnection closed by server")
                break

# Run the client
asyncio.run(test_websocket())