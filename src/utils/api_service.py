import aiohttp
from typing import Tuple, Optional
import logging
import asyncio
from aiohttp import ClientTimeout
from .file_utils import check_race_file_exists, get_race_file_name
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add constants for retry configuration
MAX_RETRIES = 3
BASE_TIMEOUT = 900  # 15 minutes in seconds
RETRY_DELAYS = [30, 60, 120]  # Exponential backoff delays in seconds

async def _fetch_race_data(race_name: str, year: int = 2024) -> Tuple[bool, str]:
    """
    Fetch race data from the F1 API for a specific race.
    Makes a GET request to http://localhost:8000/race/{year}/{race}
    
    Args:
        race_name: The normalized race name to fetch data for (format: RaceName_Year_Race)
        year: The year. Defaults to 2024.
        
    Returns:
        Tuple[bool, str]: (success, error_message)
            - success: Whether the data was successfully fetched and saved
            - error_message: Error message if unsuccessful, empty string if successful
    """

    # Keeping it simple, if continue to build break out API into queue with polling to get or another websocket
    timeout = ClientTimeout(total=BASE_TIMEOUT)  # 15 minute timeout
    
    for attempt in range(MAX_RETRIES):
        try:
            url = f"http://localhost:8000/race/{year}/{race_name}"
            logger.info(f"Attempt {attempt + 1}/{MAX_RETRIES}: Fetching race data from: {url}")
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        if attempt < MAX_RETRIES - 1:
                            delay = RETRY_DELAYS[attempt]
                            logger.warning(f"Request failed, retrying in {delay} seconds...")
                            await asyncio.sleep(delay)
                            continue
                        return False, f"API request failed with status {response.status}"
                    
                    # Verify we received the expected content type
                    content_type = response.headers.get('content-type', '')
                    if 'text/plain' not in content_type:
                        return False, f"Unexpected content type: {content_type}"
                    
                    cache_dir = os.path.join("src", "race-data-cache", "less_data")
                    os.makedirs(cache_dir, exist_ok=True)
                    
                    # Save the response content to a file
                    file_path = os.path.join(cache_dir, get_race_file_name(race_name))
                    content = await response.read()
                    
                    with open(file_path, 'wb') as f:
                        f.write(content)
                        
                    logger.info(f"Successfully saved race data to: {file_path}")
                    return True, ""
                    
        except asyncio.TimeoutError:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                logger.warning(f"Request timed out, retrying in {delay} seconds...")
                await asyncio.sleep(delay)
                continue
            return False, "Request timed out after all retry attempts"
            
        except aiohttp.ClientError as e:
            return False, f"HTTP request failed: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

async def fetch_new_race_data(normalized_race_name: str, year: int) -> Tuple[bool, str, Optional[str]]:
    """
    Fetches new race data from the F1 API and saves it locally.
    This should only be called when we know we need new data.
    
    Args:
        normalized_race_name: The validated and normalized race name
        
    Returns:
        Tuple[bool, str, Optional[str]]: (success, error_message, file_path)
            - success: Whether the data was successfully fetched and saved
            - error_message: Error message if unsuccessful, empty string if successful
            - file_path: Path to the newly created race data file if successful, None if unsuccessful
            
    Note:
        This function will always attempt to fetch fresh data from the API,
        regardless of whether a local file exists. Use check_race_data_availability
        first if you want to check for existing data.
    """
    success, error_message = await _fetch_race_data(normalized_race_name, year)
    
    if not success:
        return False, f"Failed to fetch race data: {error_message}", None
        
    # After fetch, check for the newly created file
    file_exists, file_path = check_race_file_exists(normalized_race_name, year)
    if not file_exists:
        return False, "Race data was fetched but file was not created properly", None
        
    return True, "", file_path