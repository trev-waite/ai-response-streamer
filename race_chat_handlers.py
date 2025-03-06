import asyncio
import json
from google import genai
import os

# Configure the Google Gemini API key
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def race_stream_response(prompt, queue, loop):
    try:
        print(f"Processing race chat prompt: {prompt}")
        
        # Add racing context to the prompt
        racing_context = "As a racing expert, respond to: "
        enhanced_prompt = racing_context + prompt
        
        async for chunk in await client.aio.models.generate_content_stream(
            model='gemini-2.0-flash',
            contents=enhanced_prompt
        ):
            message = {
                "type": "fromSocket",
                "content": chunk.text,
                "source": "race-chat",
                "timestamp": None
            }
            await queue.put(json.dumps(message))
        await queue.put(None)
    except Exception as e:
        error_message = {
            "type": "error",
            "content": f"Race Chat Error: {str(e)}",
            "source": "race-chat",
            "timestamp": None
        }
        await queue.put(json.dumps(error_message))
        await queue.put(None)

async def handle_race_client(websocket):
    client_id = id(websocket)
    print(f"New race chat client connected. ID: {client_id}")
    
    loop = asyncio.get_running_loop()
    
    try:
        while True:
            raw_message = await websocket.recv()
            try:
                message_data = json.loads(raw_message)
                
                if message_data.get('type') == 'ping':
                    print("Received ping from race chat client - continuing")
                    continue
                
                content = message_data.get('content')
                print(f"Received race chat prompt from client {client_id}: {content}")
            except Exception as e:
                print(f"Invalid message received from race chat client {client_id}: {str(e)}")
                continue

            queue = asyncio.Queue()
            loop.run_in_executor(None, lambda: asyncio.run(race_stream_response(content, queue, loop)))
            
            while True:
                chunk = await queue.get()
                if chunk is None:
                    done_message = {
                        "type": "done",
                        "content": "",
                        "source": "race-chat",
                        "timestamp": None
                    }
                    await websocket.send(json.dumps(done_message))
                    print("Race chat stream completed")
                    break
                await websocket.send(chunk)
    
    except json.JSONDecodeError as e:
        print(f"Invalid JSON received from race chat client {client_id}: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in race chat handler for client {client_id}: {str(e)}")
        await websocket.close(code=1011, reason=str(e))
