import asyncio
import websockets
from google import genai
import os

# Configure the Google Gemini API key
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def stream_response(prompt):
    try:
        # Generate content with streaming enabled
        for chunk in client.models.generate_content_stream(
            model='gemini-2.0-flash',
            contents=prompt
        ):
            print(chunk.text)
    except Exception as e:
        # Catch other unexpected errors
        error_msg = f"Unexpected Error: {str(e)}"
        print(error_msg)

def file_upload_question(promp):
    file = client.files.upload(file='race_data_Bahrain_2024_Race-large.txt')
    response = client.models.generate_content(
        model='gemini-2.0-flash-001',
        contents=['What was landos lap one time, why was it like that? ALso give a brief overview of the race', file]
        )
    print(response.text)
    client.files.delete(name=file.name)


# stream_response("Tell me a short story about a cat.")
file_upload_question("Could you summarize this file?")