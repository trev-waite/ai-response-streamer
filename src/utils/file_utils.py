import os
from typing import Tuple

def get_race_file_name(race_name: str, year: int = 2024) -> str:
    """
    Generate the standardized file name for a race data file.
    
    Args:
        race_name: The race name (city name)
        
    Returns:
        str: The formatted file name
    """
    formatted_race_name = race_name.replace(" ", "-")
    return f"race_data_{formatted_race_name}_{year}_Race.txt"

def check_race_file_exists(normalized_race_name: str, year: int) -> Tuple[bool, str]:
    """
    Check if a race data file exists for the given normalized race name.
    
    Args:
        normalized_race_name: The normalized race name (city name)
        
    Returns:
        Tuple[bool, str]: (file_exists, file_path)
            - file_exists: Whether the file exists
            - file_path: The full path to the file if it exists, empty string if it doesn't
    """
    # Construct the expected file path
    file_name = get_race_file_name(normalized_race_name, year)
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                            "race-data-cache", "less_data", file_name)
    
    exists = os.path.isfile(file_path)
    return exists, file_path if exists else ""