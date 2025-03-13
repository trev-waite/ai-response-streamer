import asyncio
import json
from google import genai
import os

# Configure the Google Gemini API key
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

async def race_stream_response(prompt, race_name, queue, loop):
    try:
        print(f"Processing race chat prompt for {race_name}: {prompt}")
        
        # Construct the file path based on race name  race_data_Hungarian_2024_Race
        file_path = f"./race-data/race_data_{race_name}_2024_Race.txt"
        
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
                "type": "fromSocket",
                "content": chunk.text,
                "source": "race-chat",
                "timestamp": None
            }
            await queue.put(json.dumps(message))
            
        # Cleanup: Delete the uploaded file
        client.files.delete(name=file.name)
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
            message_data = json.loads(raw_message)
            
            if message_data.get('type') == 'ping':
                print("Received ping from race chat client - continuing")
                continue
            
            content = message_data.get('content')
            race_name = message_data.get('race')
            
            if not race_name:
                raise ValueError("Race name not provided in message")
                
            print(f"Received race chat prompt from client {client_id} for race {race_name}: {content}")
            
            queue = asyncio.Queue()
            await race_stream_response(content, race_name, queue, loop)
            
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
