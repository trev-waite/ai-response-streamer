import asyncio
import json
from google import genai
import os
from utils.file_utils import check_race_file_exists
from utils.input_validator import validate_inputs
from utils.api_service import fetch_new_race_data
import websockets.exceptions

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_MAPPINGS = {
    '2.5 Pro': 'gemini-2.5-pro-preview-03-25',
    '2.5 Flash': 'gemini-2.5-flash-preview-04-17',
    '2.0 Flash': 'gemini-2.0-flash'
}

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

async def race_stream_response(prompt, data_file_path, queue, model_name='gemini-2.0-flash'):
    try:   
        file = client.files.upload(file=data_file_path)

        prompt = """You are a racing expert. The uploaded file provides race overview stats at the top, and then all 20 drivers stats by lap. The beginning of each drivers stats is like this
        DRIVER: Driver name (#driver number)
        Team: Team name
        --------------------------------------------------

        PERFORMANCE SUMMARY:
        Fastest Lap: Lap number of this driver's fastest lap - lap time of this driver's fastest lap
        Average Lap Time: average lap time for this driver's race

        LAP-BY-LAP DETAILS:
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
        
        async for chunk in await client.aio.models.generate_content_stream(
            model=model_name,
            contents=[prompt, file]
        ):
            message = {
                "role": "assistant",
                "response": chunk.text,
                "isDone": False,
                "isGettingRaceData": False,
                "timestamp": None
            }
            await queue.put(json.dumps(message))
            
        # Cleanup: Delete the uploaded file
        client.files.delete(name=file.name)
        await queue.put(json.dumps({
            "role": "assistant",
            "response": "done message",
            "isDone": True,
            "isGettingRaceData": False,
            "timestamp": None
        }))
        await queue.put(None)
    except Exception as e:
        await _send_error_message(queue, "Error getting race data from LLM", e)

async def _monitor_progress(websocket, queue, normalized_race_name):
    """Monitor progress and send updates to the client"""
    try:
        progress_messages = [
            f"Fetching race data for {normalized_race_name}. This can take several minutes...",
            "Still fetching race data...",
            "Processing race data...",
            "Formatting race data for response...",
            "Generating response...",
            "Collecting final race statistics...",
            "Getting more of the stuff...",
            "Wrapping things up...",
            "Finalizing response... Almost there!"
        ]
        
        for message in progress_messages:
            try:  # Send a new message every minute
                update = {
                    "role": "assistant",
                    "response": message,
                    "isDone": False,
                    "isGettingRaceData": True,
                    "timestamp": None
                }
                try:
                    await websocket.send(json.dumps(update))
                    await asyncio.sleep(75)
                except websockets.exceptions.ConnectionClosed:
                    return
            except asyncio.CancelledError:
                return
    except Exception as e:
        print(f"Error in progress monitoring: {str(e)}", flush=True)

async def handle_race_client(websocket):
    client_id = id(websocket)
    print(f"New race chat client connected. ID: {client_id}", flush=True)
    current_queue = None
    current_processor = None
    
    try:
        while True:
            try:
                raw_message = await websocket.recv()
                
                try:
                    # Clean up previous queue and processor if they exist
                    if current_queue and current_processor:
                        await current_queue.put(None)
                        await current_processor
                    
                    current_queue = asyncio.Queue()
                    
                    message_data = json.loads(raw_message)
                    
                    if message_data.get('role') == 'ping':
                        print("Received ping from race chat client - continuing", flush=True)
                        continue
                    
                    prompt = message_data.get('prompt')
                    race_name = message_data.get('race')
                    race_year = message_data.get('year', 2024)  # Default to 2024
                    model_name = message_data.get('model')

                    print(f"Received race chat prompt from client {client_id}: {prompt}", flush=True)
                    
                    if not race_name:
                        raise ValueError("Race name not provided in message")
                    
                    # Validate inputs
                    is_valid, error_message, validated_data = validate_inputs(race_year, race_name)
                    if not is_valid:
                        await _send_error_message(current_queue, f"Invalid input: {error_message}")
                        await current_queue.put(None)
                        await current_processor
                        continue
                    
                    normalized_race_name = validated_data['race_name']
                    validated_year = validated_data['year']
                    
                    print(f"Processing request from client {client_id}\n Race: {normalized_race_name} \n Year: {validated_year} \n Model: {model_name}", flush=True)
                    
                    # First check if we have the data locally
                    file_exists, file_path = check_race_file_exists(normalized_race_name, validated_year)
                    if not file_exists:
                        current_processor = asyncio.create_task(process_messages(websocket, current_queue))
                        fetch_task = asyncio.create_task(fetch_new_race_data(normalized_race_name, validated_year))
                        progress_task = asyncio.create_task(_monitor_progress(websocket, current_queue, normalized_race_name))
                        
                        try:
                            success, error_message, file_path = await fetch_task
                            progress_task.cancel()
                            current_processor.cancel()
                            
                            if not success:
                                await _send_error_message(current_queue, error_message)
                                await current_queue.put(None)
                                await current_processor
                                continue
                                
                        except Exception as e:
                            progress_task.cancel()
                            await _send_error_message(current_queue, str(e))
                            await current_queue.put(None)
                            await current_processor
                            continue
                    
                    # Reset queue and processor for Gemini response
                    current_queue = asyncio.Queue()
                    current_processor = asyncio.create_task(process_messages(websocket, current_queue))
                    gemini_model_name = MODEL_MAPPINGS.get(model_name, 'gemini-2.0-flash')
                    response_task = asyncio.create_task(race_stream_response(prompt, file_path, current_queue, gemini_model_name))

                    print(f"Race chat stream completed with for Client: {client_id}", flush=True)
                    
                    await response_task
                    await current_queue.put(None)
                    await current_processor
                    
                except json.JSONDecodeError as e:
                    print(f"Invalid JSON received from race chat client {client_id}: {str(e)}", flush=True)
                    await _send_error_message(current_queue, "Invalid JSON received", e)
                    await current_queue.put(None)
                    await current_processor
                except Exception as e:
                    print(f"Invalid message received from race chat client {client_id}: {str(e)}", flush=True)
                    await _send_error_message(current_queue, "Invalid message format received from client", e)
                    await current_queue.put(None)
                    await current_processor
                    continue
            except websockets.exceptions.ConnectionClosed:
                print(f"Client {client_id} disconnected", flush=True)
                break
    except Exception as e:
        print(f"Unexpected error in race chat handler for client {client_id}: {str(e)}", flush=True)
        if current_queue and current_processor:
            await current_queue.put(None)
            await current_processor
        await websocket.close(code=1011, reason=str(e))

async def process_messages(websocket, queue):
    try:
        while True:
            message = await queue.get()
            if message is None:
                break
            try:
                await websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                break
    except asyncio.CancelledError:
        pass

async def _send_error_message(queue, error_message, e=None):
    print(f"Sending error message: {error_message}", flush=True)
    if e:
        print(f"Exception: {e}", flush=True)
    error_message = {
        "role": "error",
        "response": error_message,
        "isDone": True,
        "timestamp": None
    }
    await queue.put(json.dumps(error_message))
