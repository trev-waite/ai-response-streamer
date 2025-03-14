import asyncio
import websockets
import json
import time

async def test_websocket():
    uri = "ws://localhost:8765/race-chat"
    
    async with websockets.connect(uri) as websocket:
        # Create message following the WebSocketMessage interface
        # Tell me a bit about how max throttle usage changed throughout the race
        # What drivers participaded in this race?
        # What was max's lap 12 sector 1 time, how does it compare to his other laps?
        # Tell me a bit about Oscars race, and why he did how he did
        # "Did the weather play a factor in the race, and also how did maxs throttle usage change throughout the race"
        #  What was max verstapans throttle usage on the 5th lap
        # Tell me a bit about Oscars race, and why he did how he did, and compare his strategy with leclercs
        message = {
            "type": "fromClient",
            "content": "Can you tell me about Piastris throttle usage compared to leclercs",
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
                if message_data["type"] == "done":
                    print("\nStream completed")
                    break
                elif message_data["type"] == "error":
                    print(f"\nError: {message_data['content']}")
                    break
                else:
                    print(message_data["content"], end="", flush=True)
                    
            except websockets.ConnectionClosed:
                print("\nConnection closed by server")
                break

# Run the client
asyncio.run(test_websocket())