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

# Load the model, index, and chunks
model = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.read_index('embedding/v2_local/outputs/faiss_index.bin')
with open('embedding/v2_local/outputs/chunks.pkl', 'rb') as f:
    chunks = pickle.load(f)

# Configure the Google Gemini API key
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
        # Embed the prompt locally
        prompt_embedding = await loop.run_in_executor(None, lambda: model.encode(prompt))
        
        # Search for top-k similar chunks
        k = 5
        distances, indices = await loop.run_in_executor(
            None,
            lambda: index.search(np.array([prompt_embedding]).astype('float32'), k)
        )
        
        # Retrieve relevant chunks
        relevant_chunks = [chunks[i] for i in indices[0] if i < len(chunks)]
        context = " ".join(relevant_chunks) if relevant_chunks else "No context available."
        
        # Construct enhanced prompt
        enhanced_prompt = f"Based on this context: {context}, answer: {prompt}"
        
        # Send to Google API (assuming client is your API client)
        async for chunk in await client.aio.models.generate_content_stream(
            model='gemini-2.0-flash',  # Replace with your model
            contents=enhanced_prompt
        ):
            message = {"type": "fromSocket", "content": chunk.text, "source": "race-chat"}
            await queue.put(json.dumps(message))
        await queue.put(None)
    except Exception as e:
        await queue.put(json.dumps({"type": "error", "content": str(e)}))
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
            # Directly await the async function instead of using run_in_executor
            await race_stream_response(content, queue, loop)
            
            # Send response chunks to the client
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