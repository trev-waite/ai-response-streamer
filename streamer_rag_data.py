import asyncio
import websockets
from google import genai
import os
import json
from embedding.v2_local.race_chat_handlers_with_embedding_v2 import handle_race_client

# TODO: Update input andoutput formats to match the new objects

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def stream_response(prompt, queue, loop):
    try:
        print(f"Processing prompt: {prompt}")
        async for chunk in await client.aio.models.generate_content_stream(
            model='gemini-2.0-flash',
            contents=prompt
        ):
            message = {
                "type": "fromSocket",
                "content": chunk.text,
                "timestamp": None
            }
            await queue.put(json.dumps(message))
        await queue.put(None)
    except Exception as e:
        error_message = {
            "type": "error",
            "content": f"Unexpected Error: {str(e)}",
            "timestamp": None
        }
        await queue.put(json.dumps(error_message))
        await queue.put(None)

async def handle_client(websocket):
    client_id = id(websocket)
    print(f"New client connected. ID: {client_id}")
    
    loop = asyncio.get_running_loop()
    
    try:
        while True:
            raw_message = await websocket.recv()
            try:
                message_data = json.loads(raw_message)
                
                if message_data.get('type') == 'ping':
                    print("Received ping from client - continuing")
                    continue
                
                content = message_data.get('content')
                print(f"Received prompt from client {client_id}: {content}")
            except Exception as e:
                print(f"Invalid message received from client {client_id}: {str(e)}")
                continue

            queue = asyncio.Queue()
            await asyncio.run(stream_response(content, queue, loop))
            
            while True:
                chunk = await queue.get()
                if chunk is None:
                    done_message = {
                        "type": "done",
                        "content": "",
                        "timestamp": None
                    }
                    await websocket.send(json.dumps(done_message))
                    print("Stream completed")
                    break
                await websocket.send(chunk)
    
    except json.JSONDecodeError as e:
        print(f"Invalid JSON received from client {client_id}: {str(e)}")
    except websockets.exceptions.ConnectionClosedOK:
        print(f"Client {client_id} disconnected normally (code 1000)")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Client {client_id} disconnected with error: {e.code} - {e.reason}")
    except Exception as e:
        print(f"Unexpected error in handler for client {client_id}: {str(e)}")
        await websocket.close(code=1011, reason=str(e))

async def main():
    try:
        routes = {
            "/chat": handle_client,
            "/race-chat-v2": handle_race_client,
            "/": handle_client
        }

        async def route_handler(websocket):
            path = websocket.request.path
            if path in routes:
                await routes[path](websocket)
            else:
                await websocket.close(4004, f"Path {path} not found")

        server = await websockets.serve(route_handler, "localhost", 8765)
        print("WebSocket server started on ws://localhost:8765")
        print("Available endpoints: /, /chat, and /race-chat-v2")
        await server.wait_closed()
    except OSError as e:
        print(f"Failed to start server (port may be in use): {str(e)}")
    except Exception as e:
        print(f"Server startup error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())