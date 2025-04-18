import asyncio
import json
from google import genai
import os
import faiss
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer

# Add in below before startting server
#  --------------------------------------------------------------------------  #
# from sentence_transformers import SentenceTransformer
# import faiss
# import pickle

model = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.read_index('embedding/v2_local/outputs/faiss_index.bin')
with open('embedding/v2_local/outputs/chunks.pkl', 'rb') as f:
    chunks = pickle.load(f)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def race_stream_response(prompt, queue, loop):
    """
    Generates a streaming response for a race chat prompt using context from a large file.
    
    Args:
        prompt (str): The user's input prompt.
        queue (asyncio.Queue): Queue to send response chunks to the client.
        loop (asyncio.AbstractEventLoop): The event loop for running synchronous tasks.
    """
    try:
        prompt_embedding = await loop.run_in_executor(None, lambda: model.encode(prompt))
        
        # Search for top-k similar chunks
        k = 10 
        distances, indices = await loop.run_in_executor(
            None,
            lambda: index.search(np.array([prompt_embedding]).astype('float32'), k)
        )
        
        relevant_chunks = [chunks[i] for i in indices[0] if i < len(chunks)]
        context = " ".join(relevant_chunks) if relevant_chunks else "No context available."
        
        # print('---------------------------', flush=True)
        # print(context, flush=True)
        # print('---------------------------', flush=True)
        # Debugging use above

        enhanced_prompt = f"I am giving you context from a 2024 F1 car race. Use it to answer the question. Context: {context}, Question: {prompt}"
        
        async for chunk in await client.aio.models.generate_content_stream(
            model='gemini-2.0-flash',
            contents=enhanced_prompt
        ):
            message = {
                "role": "assistant",
                "response": chunk.text,
                "isDone": False,
                "timestamp": None
            }
            await queue.put(json.dumps(message))
        await queue.put(json.dumps({
            "role": "assistant",
            "response": "done message",
            "isDone": True,
            "timestamp": None
        }))
        print("Race chat stream completed")
    except Exception as e:
        await queue.put(json.dumps({
            "role": "error",
            "response": "Error getting race data response",
            "isDone": True,
            "timestamp": None
        }))

async def handle_race_client(websocket):
    """
    Handles WebSocket connections for race chat clients.
    
    Args:
        websocket: The WebSocket connection object.
    """
    client_id = id(websocket)
    print(f"New race chat client connected. ID: {client_id}", flush=True)
    
    loop = asyncio.get_running_loop()
    
    try:
        while True:
            raw_message = await websocket.recv()
            try:
                message_data = json.loads(raw_message)
                
                if message_data.get('role') == 'ping':
                    print("Received ping from race chat client - continuing", flush=True)
                    continue
                
                prompt = message_data.get('prompt')
                print(f"Received race chat prompt from client {client_id}: {prompt}", flush=True)
            except Exception as e:
                print(f"Invalid message received from race chat client {client_id}: {str(e)}", flush=True)
                continue

            queue = asyncio.Queue()
            asyncio.create_task(race_stream_response(prompt, queue, loop))
            
            while True:
                chunk = await queue.get()
                await websocket.send(chunk)
    
    except json.JSONDecodeError as e:
        print(f"Invalid JSON received from race chat client {client_id}: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in race chat handler for client {client_id}: {str(e)}")
        await websocket.close(code=1011, reason=str(e))