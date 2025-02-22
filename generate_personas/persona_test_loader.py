import os
import json
import random
from config import TEST_CASES_DIR, PERSONA_CREATION_DIR
from gp_db_utils import insert_persona_foundation


def load_test_cases(logger, file_name, directory=TEST_CASES_DIR, validate_test_cases=False):
    """
    Load test case JSON data from the specified directory. Optionally validate test case JSON structure.

    Args:
        file_name (str): The name of the JSON file to load.
        directory (str): The directory where the JSON file is located.
        validate_test_cases (bool): Whether to validate the JSON structure for test cases.

    Returns:
        dict: The loaded JSON data, with prompt types explicitly included.

    Raises:
        ValueError: If test case validation fails.
        Exception: For other file loading errors.
    """
    file_path = f"{directory}/{file_name}"
    data = None  # Define `data` at the start
    try:
        logger.debug(f"[loader] Loading file: {file_path}")
        with open(file_path, "r") as f:
            data = json.load(f)

            # Validate test cases if required
            if validate_test_cases:
                required_keys = ["system_messages", "structured_prompts", "freeform_prompts"]
                missing_keys = [key for key in required_keys if key not in data]
                if missing_keys:
                    raise ValueError(f"JSON file is missing required keys: {', '.join(missing_keys)}")

                # Ensure system_messages are strings
                if not isinstance(data["system_messages"], dict):
                    raise ValueError("system_messages must be a dictionary.")
                for key, value in data["system_messages"].items():
                    if not isinstance(value, str):
                        raise ValueError(f"[loader] system_messages[{key}] must be a string, got {type(value).__name__}.")

                # Validate structured_prompts and freeform_prompts
                for prompt_type in ["structured_prompts", "freeform_prompts"]:
                    if prompt_type in data:
                        if not isinstance(data[prompt_type], list):
                            raise ValueError(f"{prompt_type} must be a list.")
                        for prompt in data[prompt_type]:
                            if not isinstance(prompt, dict):
                                raise ValueError(f"Each {prompt_type} entry must be a dictionary, got {type(prompt).__name__}.")
                            if "prompt_id" not in prompt or not isinstance(prompt["prompt_id"], int):
                                raise ValueError(f"Each {prompt_type} entry must have an integer 'prompt_id'.")

            # Validate and normalize detail_level
            detail_level = data.get("detail_level")
            if not detail_level:
                raise ValueError("[loader] JSON file is missing the required key: 'detail_level'.")
            if isinstance(detail_level, str):
                data["detail_level"] = [detail_level]
                logger.info(f"[loader] Converted detail_level to list: {data['detail_level']}")
            elif not isinstance(detail_level, list) or not all(isinstance(dl, str) for dl in detail_level):
                raise ValueError("[loader] detail_level must be a string or a list of strings.")

            # Add explicit prompt type to each prompt
            for prompt_type in ["freeform_prompts", "structured_prompts"]:
                if prompt_type in data:
                    for prompt in data[prompt_type]:
                        prompt["prompt_type"] = prompt_type  # Add 'prompt_type' key

            # Set default model if not defined
            if "open_ai_model" not in data or not isinstance(data["open_ai_model"], str):
                logger.warning("[loader] open_ai_model not defined in JSON. Defaulting to 'gpt-3.5-turbo'.")
                data["open_ai_model"] = "gpt-3.5-turbo"

            logger.debug(f"[loader] Loaded JSON data: {data} (type: {type(data)})")
            return data
    except FileNotFoundError:
        logger.error(f"[loader] File not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"[loader] Invalid JSON format in {file_path}: {e}")
        raise
    except Exception as e:
        logger.error(f"[loader] Error loading JSON file {file_path}: {e}")
        raise


def load_persona_data(logger, file_name):
    """
    Load JSON data specifically from the persona-creation directory for persona generation.

    Args:
        file_name (str): The name of the JSON file to load.

    Returns:
        list or dict: The loaded JSON data.
    """
    try:
        file_path = os.path.join(PERSONA_CREATION_DIR, file_name)
        logger.info(f"[loader] Loading {file_name} for persona foundation...")
        with open(file_path, "r") as f:
            data = json.load(f)
            
            # Validate simple lists
            if isinstance(data, list) and file_name != "locations-specific.json":
                return data

            # Validate locations-specific.json
            if file_name == "locations-specific.json":
                if not all(isinstance(entry, dict) and "Country" in entry and "States" in entry for entry in data):
                    raise ValueError(f"[loader] Invalid format in {file_name}. Expected a list of dictionaries with 'Country' and 'States' keys.")
                return data

            # Raise error for unexpected formats
            raise ValueError(f"[loader] Unexpected data format in {file_name}. Expected a list or specific structure for locations.")
    except Exception as e:
        logger.error(f"[loader] Error loading JSON file {file_name}: {e}")
        raise



def generate_persona_foundation(logger):
    """
    Generate a persona foundation using randomized data from the libraries in the persona creation directory.

    Returns:
        dict: A dictionary containing persona details.
    """
    try:
        first_names = load_persona_data(logger, "names-first.json")
        last_names = load_persona_data(logger, "names-last.json")
        animals_data = load_persona_data(logger, "animals.json")
        specific_locations = load_persona_data(logger, "locations-specific.json")
        generic_locations = load_persona_data(logger, "locations-generic.json")

        pronouns = ["he/him", "she/her", "they/them"]
        relationship_status = ["single", "married", "in a relationship", "divorced"]

        country = random.choice(specific_locations)
        if not country["States"]:
            location = random.choice(generic_locations)
        else:
            state = random.choice(country["States"])
            if not state["Cities"]:
                location = state["State"]
            else:
                city = random.choice(state["Cities"])
                location = f"{city}, {state['State']}, {country['Country']}"

        foundation = {
            "name": f"{random.choice(first_names)} {random.choice(last_names)}",
            "age": random.randint(20, 80),
            "location": location,
            "pronoun": random.choice(pronouns),
            "relationship_status": random.choice(relationship_status),
            "children": random.randint(0, 5),
            "pets": random.choice(animals_data),
        }

        logger.info(f"[loader] Generated persona foundation: {foundation}")
        return foundation

    except Exception as e:
        logger.error(f"[loader] Error generating persona foundation: {e}")
        raise

def store_persona(logger, cursor, foundation, test_run_id):
    """
    Store a persona foundation in the database.

    Args:
        cursor: Database cursor.
        foundation (dict): The persona foundation to store.
        test_run_id: The test run ID associated with the persona.

    Returns:
        int: The ID of the inserted persona.
    """
    try:
        # Insert the persona into the database
        persona_id = insert_persona_foundation(logger, cursor, foundation, test_run_id)
        logger.info(f"[loader] Persona stored with ID: {persona_id}")
        return persona_id
    except Exception as e:
        logger.error(f"[loader] Error storing persona: {e}")
        raise