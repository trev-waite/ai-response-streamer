import asyncio
import json
from google import genai
import os
import faiss
import numpy as np
import pickle

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Load precomputed chunks and FAISS index
with open('chunks.pkl', 'rb') as f:
    chunks = pickle.load(f)
index = faiss.read_index('racing_data.index')

async def race_stream_response(prompt, queue, loop):
    """
    Generates a streaming response for a race chat prompt using context from a large file.
    
    Args:
        prompt (str): The user's input prompt.
        queue (asyncio.Queue): Queue to send response chunks to the client.
        loop (asyncio.AbstractEventLoop): The event loop for running synchronous tasks.
    """
    try:
        print(f"Processing race chat prompt: {prompt}")
        
        prompt_embedding = await loop.run_in_executor(
            None,
            lambda: client.embed_content(model='embedding-model', content=prompt)
        )
        
        # Search FAISS index for top-k similar chunks
        k = 3
        distances, indices = await loop.run_in_executor(
            None,
            lambda: index.search(np.array([prompt_embedding]).astype('float32'), k)
        )
        
        relevant_chunks = [chunks[i] for i in indices[0] if i < len(chunks)]
        context = " ".join(relevant_chunks) if relevant_chunks else "No additional context available."
        
        enhanced_prompt = f"As a racing expert, based on the following information: {context}, respond to: {prompt}"

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
        await queue.put(None)  # Signal end of stream
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
    """
    Handles WebSocket connections for race chat clients.
    
    Args:
        websocket: The WebSocket connection object.
    """
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
            asyncio.create_task(race_stream_response(content, queue, loop))
            
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