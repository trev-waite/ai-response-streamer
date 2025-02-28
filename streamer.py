import asyncio
import websockets
from google import genai
import os

# Configure the Google Gemini API key
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def stream_response(prompt, queue, loop):
    try:
        print(f"Processing prompt: {prompt}")
        async for chunk in await client.aio.models.generate_content_stream(
            model='gemini-2.0-flash',
            contents=prompt
        ):
            await queue.put(chunk.text)
        await queue.put(None)
    except Exception as e:
        error_msg = f"Unexpected Error: {str(e)}"
        await queue.put(error_msg)
        await queue.put(None)

async def handle_client(websocket):
    client_id = id(websocket)  # Get a unique ID for the client
    print(f"New client connected. ID: {client_id}")
    
    loop = asyncio.get_running_loop()
    
    try:
        while True:
            message = await websocket.recv()
            # Check if message is a ping
            if '"type":"ping"' in message:
                print("Received ping from client - continuing")
                continue
                
            print(f"Received prompt from client {client_id}: {message}")

            queue = asyncio.Queue()
            loop.run_in_executor(None, lambda: asyncio.run(stream_response(message, queue, loop)))
            
            while True:
                chunk = await queue.get()
                if chunk is None:
                    await websocket.send("[DONE]")
                    print("Stream completed")
                    break
                print(f"Sending chunk: {chunk}")
                await websocket.send(chunk)
    
    except websockets.exceptions.ConnectionClosedOK:
        print(f"Client {client_id} disconnected normally (code 1000)")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Client {client_id} disconnected with error: {e.code} - {e.reason}")
    except Exception as e:
        print(f"Unexpected error in handler for client {client_id}: {str(e)}")
        await websocket.close(code=1011, reason=str(e))

async def main():
    try:
        server = await websockets.serve(handle_client, "localhost", 8765)
        print("WebSocket server started on ws://localhost:8765")
        await server.wait_closed()
    except OSError as e:
        print(f"Failed to start server (port may be in use): {str(e)}")
    except Exception as e:
        print(f"Server startup error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())