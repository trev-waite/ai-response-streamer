import asyncio
import json
from google import genai
import os

# Configure the Google Gemini API key
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Message format from user
# MessageFromUser {
#   role: 'user' | 'ping';
#   prompt: string;
#   race: string;
#   timestamp: number;
#}

# MessageFromAsssistant { 
#   role: 'assistant' | 'error'; 
#   response: string; 
#   isDone: boolean; 
#   timestamp: Date; 
# }

async def race_stream_response(prompt, race_name, queue):
    try:
        print(f"Processing race chat prompt for {race_name}: {prompt}", flush=True)
        
        # Construct the file path based on race name  race_data_Hungarian_2024_Race
        file_path = f"./race-data/less_data/race_data_{race_name}_2024_Race.txt"
        
        # Upload the race data file
        file = client.files.upload(file=file_path)

        prompt = """You are a racing expert. The uploaded file provides race overview stats at the top, and then all 20 drivers stats by lap. The beginning of each drivers stats is like this
        DRIVER: Driver name (#driver number)
        Team: Team name
        --------------------------------------------------
        Each lap has the following data:
        Time: time of lap
        Sectors:
          S1: Sector 1 time
          S2: Sector 2 time
          S3: Sector 3 time
        Speed Traps (km/h):
          Trap 1: Speed trap 1 time
          Trap 2: Speed trap 2 time
          Trap 3: Speed trap 3 time
        Tire Compound: Tire compound used
        Lap Status:
          Personal Best: Is it the driver's personal best lap
        Telemetry Stats:
          Max Speed: max speed of lap
          Avg Speed: average speed of lap
          Throttle Usage Stats:
            - Full Throttle (≥95%): Percentage of lap used at full throttle
            - Partial Throttle (5-95%): percentage of lap used at partial throttle
            - No Throttle (≤5%): percentage of lap used with no throttle
            - Average Throttle: average throttle usage of lap
          Brake Usage Stats:
            - Time on Brakes: percent of lap spent on brakes
            - Brake Applications: number of brake applications from race samples
            - Distinct Brake Zones: number of distinct brake zones
        Use that to help you find driver specific data. In your answer back don't mention from the provided data, just answer the question. 
        Also if you're giving data back to the user, display in a nice, easy to read, way that also looks good. Feel free to use markup when needed. Prompt: """ + prompt
        
        # Stream the response with both the prompt and file context
        async for chunk in await client.aio.models.generate_content_stream(
            model='gemini-2.0-flash',
            contents=[prompt, file]
        ):
            message = {
                "role": "assistant",
                "response": chunk.text,
                "isDone": False,
                "timestamp": None
            }
            await queue.put(json.dumps(message))
            
        # Cleanup: Delete the uploaded file
        client.files.delete(name=file.name)
        await queue.put(json.dumps({
            "role": "assistant",
            "response": "done message",
            "isDone": True,
            "timestamp": None
        }))
        print("Race chat stream completed", flush=True)
    except Exception as e:
        await _send_error_message(queue, "Error getting race data from LLM")

async def handle_race_client(websocket):
    client_id = id(websocket)
    print(f"New race chat client connected. ID: {client_id}", flush=True)
    
    try:
        while True:
            raw_message = await websocket.recv()
            try:
                message_data = json.loads(raw_message)
                
                if message_data.get('role') == 'ping':
                    print("Received ping from race chat client - continuing", flush=True)
                    continue
                
                prompt = message_data.get('prompt')
                race_name = message_data.get('race')
                
                if not race_name:
                    raise ValueError("Race name not provided in message")
                
                print(f"Received race chat prompt from client {client_id} for race {race_name}: {prompt}", flush=True)
            except Exception as e:
                print(f"Invalid message received from race chat client {client_id}: {str(e)}", flush=True)
                await _send_error_message(queue, "Invalid message format received from client")
                continue

            queue = asyncio.Queue()
            asyncio.create_task(race_stream_response(prompt, race_name, queue))
            
            while True:
                chunk = await queue.get()
                await websocket.send(chunk)
    
    except json.JSONDecodeError as e:
        print(f"Invalid JSON received from race chat client {client_id}: {str(e)}", flush=True)
        await _send_error_message(queue, "Invalid JSON received")
    except Exception as e:
        print(f"Unexpected error in race chat handler for client {client_id}: {str(e)}", flush=True)
        await websocket.close(code=1011, reason=str(e))


async def _send_error_message(queue, errorMessge):
    error_message = {
            "role": "error",
            "response": errorMessge,
            "isDone": True,
            "timestamp": None
        }
    await queue.put(json.dumps(error_message))
