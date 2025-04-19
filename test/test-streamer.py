import asyncio
import websockets
import json
import time

async def test_websocket():
    uri = "ws://localhost:8765/race-chat"
    
    async with websockets.connect(uri) as websocket:
        # Create message following the WebSocketMessage interface
        message = {
            "role": "user",
            "prompt": "Can you tell me about Piastris throttle usage compared to leclercs",
            "race": "Hungarian",
            "timestamp": int(time.time() * 1000)  # Current time in milliseconds
        }
        
        # Send the JSON message
        await websocket.send(json.dumps(message))
        print(f"Sent message: {message}")
        
        # Receive and print the streamed response
        print("Response:")
        while True:
            try:
                response = await websocket.recv()
                message_data = json.loads(response)
                
                # Handle different message types
                if message_data.get("role") == "assistant" and message_data.get("isDone"):
                    print("\nStream completed")
                    break
                elif message_data.get("role") == "error":
                    print(f"\nError: {message_data.get('response')}")
                    break
                else:
                    print(message_data.get("response", ""), end="", flush=True)
                    
            except websockets.ConnectionClosed:
                print("\nConnection closed by server")
                break

# Run the client
asyncio.run(test_websocket())