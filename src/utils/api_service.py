import aiohttp
from typing import Tuple, Optional
import logging
from .file_utils import check_race_file_exists, get_race_file_name
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    try:
        url = f"http://localhost:8000/race/{year}/{race_name}"
        logger.info(f"Fetching race data from: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
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
                
    except aiohttp.ClientError as e:
        return False, f"HTTP request failed: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

async def fetch_new_race_data(normalized_race_name: str) -> Tuple[bool, str, Optional[str]]:
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
    success, error_message = await _fetch_race_data(normalized_race_name)
    
    if not success:
        return False, f"Failed to fetch race data: {error_message}", None
        
    # After fetch, check for the newly created file
    file_exists, file_path = check_race_file_exists(normalized_race_name)
    if not file_exists:
        return False, "Race data was fetched but file was not created properly", None
        
    return True, "", file_path