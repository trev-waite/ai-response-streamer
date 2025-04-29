from typing import Dict, List, Tuple, Optional, TypedDict
from datetime import datetime

class ValidatedRaceData(TypedDict):
    year: int
    race_name: str

# Define valid F1 Grand Prix names and their aliases
f1_grand_prix_names = [
    {"city": "Melbourne", "aliases": ["Australia", "Australian"]},
    {"city": "Shanghai", "aliases": ["China", "Chinese"]},
    {"city": "Suzuka", "aliases": ["Japan", "Japanese"]},
    {"city": "Sakhir", "aliases": ["Bahrain", "Bahraini"]},
    {"city": "Jeddah", "aliases": ["Saudi Arabia", "Saudi"]},
    {"city": "Miami", "aliases": []},
    {"city": "Imola", "aliases": ["Emilia Romagna"]},
    {"city": "Monaco", "aliases": []},
    {"city": "Barcelona", "aliases": ["Spain", "Spanish"]},
    {"city": "Montreal", "aliases": ["Canada", "Canadian"]},
    {"city": "Spielberg", "aliases": ["Austria", "Austrian"]},
    {"city": "Silverstone", "aliases": ["United Kingdom", "UK", "British"]},
    {"city": "Spa", "aliases": ["Belgium", "Belgian"]},
    {"city": "Budapest", "aliases": ["Hungary", "Hungarian"]},
    {"city": "Zandvoort", "aliases": ["Netherlands", "Dutch"]},
    {"city": "Monza", "aliases": ["Italy", "Italian"]},
    {"city": "Baku", "aliases": ["Azerbaijan", "Azerbaijani"]},
    {"city": "Singapore", "aliases": []},
    {"city": "Austin", "aliases": ["United States", "USA", "US", "COTA"]},
    {"city": "Mexico City", "aliases": ["Mexico", "Mexican"]},
    {"city": "São Paulo", "aliases": ["Sao Paulo", "Brazil", "Brazilian"]},
    {"city": "Las Vegas", "aliases": ["Vegas"]},
    {"city": "Lusail", "aliases": ["Qatar", "Qatari"]},
    {"city": "Abu Dhabi", "aliases": ["United Arab Emirates", "UAE"]}
]

def validate_year(year: int) -> Tuple[bool, str]:
    """
    Validate that the year is:
    1. Actually an integer
    2. Between 2015 and current year
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    try:
        year = int(year)
        current_year = datetime.now().year
        
        if not (2015 <= year <= current_year):
            return False, f"Year must be between 2015 and {current_year}"
        
        return True, ""
    except (ValueError, TypeError):
        return False, "Year must be a valid integer"

def normalize_race_name(race_name: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validate and normalize the race name input.
    Converts aliases to official city names.
    
    Args:
        race_name: The input race name or alias
        
    Returns:
        Tuple[bool, str, Optional[str]]: (is_valid, error_message, normalized_name)
            - is_valid: Whether the input is valid
            - error_message: Error message if invalid, empty string if valid
            - normalized_name: The official city name if valid, None if invalid
    """
    if not race_name:
        return False, "Race name cannot be empty", None
    
    # Normalize input by removing extra whitespace and converting to title case
    normalized_input = " ".join(race_name.strip().split())
    
    # Check if the input matches any city or alias (case-insensitive)
    for grand_prix in f1_grand_prix_names:
        if normalized_input.lower() == grand_prix["city"].lower():
            return True, "", grand_prix["city"]
        
        for alias in grand_prix["aliases"]:
            if normalized_input.lower() == alias.lower():
                return True, "", grand_prix["city"]
    
    # If no match is found
    valid_locations = ", ".join(sorted(set([gp["city"] for gp in f1_grand_prix_names])))
    return False, f"Invalid race location. Must be one of: {valid_locations} or a variation of the name", None

def validate_inputs(year: int, race_name: str) -> Tuple[bool, str, Optional[ValidatedRaceData]]:
    """
    Validate all inputs for the F1 data API.
    
    Args:
        year: The year of the race
        race_name: The name of the race location or an alias
        
    Returns:
        Tuple[bool, str, Optional[ValidatedRaceData]]: (is_valid, error_message, validated_data)
            - is_valid: Whether all inputs are valid
            - error_message: Error message if invalid, empty string if valid
            - validated_data: Typed dictionary with normalized values if valid, None if invalid
    """
    # Validate year
    year_valid, year_error = validate_year(year)
    if not year_valid:
        return False, year_error, None
    
    # Validate and normalize race name
    race_valid, race_error, normalized_race = normalize_race_name(race_name)
    if not race_valid:
        return False, race_error, None
    
    # All validations passed
    return True, "", ValidatedRaceData(
        year=int(year),
        race_name=normalized_race
    )