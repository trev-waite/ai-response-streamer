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


stream_response("Tell me a short story about a cat.")