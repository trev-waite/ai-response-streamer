import os
from typing import Tuple

def check_race_file_exists(normalized_race_name: str) -> Tuple[bool, str]:
    """
    Check if a race data file exists for the given normalized race name.
    
    Args:
        normalized_race_name: The normalized race name (city name)
        
    Returns:
        Tuple[bool, str]: (file_exists, file_path)
            - file_exists: Whether the file exists
            - file_path: The full path to the file if it exists, empty string if it doesn't
    """
    # Convert any spaces to hyphens in the race name for the filename
    formatted_race_name = normalized_race_name.replace(" ", "-")
    
    # Construct the expected file path
    file_name = f"race_data_{formatted_race_name}_2024_Race.txt"
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                            "race-data-cache", "less_data", file_name)
    
    exists = os.path.isfile(file_path)
    return exists, file_path if exists else ""