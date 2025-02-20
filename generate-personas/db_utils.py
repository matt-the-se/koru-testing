import json
import psycopg2
from config import DB_CONFIG


def connect_db(logger):
    """
    Establishes a database connection using the configuration.
    """
    logger.debug("Connecting to the database.")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("[PG db_utils] Database connection established.")
        return conn
    except Exception as e:
        logger.error(f"[PG db_utils] Error connecting to the database: {e}")
        raise

def summarize_results(logger, cursor, test_run_id):
    """
    Summarizes the results of a test run by counting the number of personas and responses generated.

    Args:
        cursor: Database cursor.
        test_run_id (int): ID of the test run to summarize.

    Returns:
        dict: Summary containing counts of personas and responses.
    """
    try:
        # Count personas
        cursor.execute("""
            SELECT COUNT(*) FROM personas WHERE test_run_id = %s;
        """, (test_run_id,))
        persona_count = cursor.fetchone()[0]

        # Count persona inputs (responses)
        cursor.execute("""
            SELECT COUNT(*) FROM persona_inputs WHERE persona_id IN (
                SELECT persona_id FROM personas WHERE test_run_id = %s
            );
        """, (test_run_id,))
        response_count = cursor.fetchone()[0]

        summary = {
            "persona_count": persona_count,
            "response_count": response_count
        }

        logger.info(f"[PG db_utils] Test run {test_run_id} complete. Generated {persona_count} personas and {response_count} inputs.")
        print(f"[PG db_utils] Test run {test_run_id} complete. Generated {persona_count} personas and {response_count} inputs.")

        return summary
    except Exception as e:
        logger.error(f"[PG db_utils] Error summarizing results for test_run_id {test_run_id}: {e}")
        raise

def insert_persona_foundation(logger, cursor, foundation, test_run_id, detail_level="varies"):
    """
    Inserts a persona foundation into the database.

    Args:
        logger: Logger instance.
        cursor: Database cursor.
        foundation: The persona foundation dictionary.
        test_run_id: The test run ID to associate the persona with.
        detail_level: The detail level of the persona (default: "varies").

    Returns:
        int: The ID of the newly inserted persona.
    """
    try:
        cursor.execute("""
            INSERT INTO personas (foundation, detail_level, test_run_id)
            VALUES (%s, %s, %s)
            RETURNING persona_id;
        """, (json.dumps(foundation), detail_level, test_run_id))
        persona_id = cursor.fetchone()[0]

        if not persona_id:
            raise ValueError("[PG db_utils] Failed to retrieve persona_id after insertion.")

        logger.info(f"[PG db_utils] Inserted persona with ID {persona_id}.")
        return persona_id
    except Exception as e:
        logger.error(f"[PG db_utils] Error inserting persona: {e}")
        raise


def insert_response(logger, cursor, persona_id, prompt_id, test_run_id, detail_level, response_text):
    """
    Inserts a response into the database.

    Args:
        cursor: Database cursor.
        persona_id: ID of the persona the response is associated with.
        prompt_id: ID of the prompt.
        test_run_id: The test run ID.
        detail_level: Detail level of the response.
        response_text: The generated response text.
    """
    try:
        cursor.execute("""
            INSERT INTO persona_inputs (
                persona_id, prompt_id, test_run_id, detail_level, response_text
            ) VALUES (%s, %s, %s, %s, %s);
        """, (persona_id, prompt_id, test_run_id, detail_level, response_text))
        logger.info(f"[PG db_utils] Inserted response for persona_id {persona_id}, prompt_id {prompt_id}.")
    except Exception as e:
        logger.error(f"[PG db_utils] Error inserting response: {e}")
        raise
def create_test_run_id(logger, cursor, file_name, model_name, test_case_data):
    """
    Create a new test run ID.

    Args:
        cursor: Database cursor.
        file_name: The name of the JSON file used for the test case.
        model_used: The model used for generating responses (e.g., gpt-3.5-turbo, gpt-4).
        test_case_data: The loaded test case JSON data.

    Returns:
        int: The newly created test run ID.
    """
    try:
        # Generate a compact parameters string
        parameters = {
            "system_messages": list(test_case_data.get("system_messages", {}).keys()),
            "detail_level": test_case_data.get("detail_level", []),
            "freeform_prompts": [prompt.get("prompt_id") for prompt in test_case_data.get("freeform_prompts", [])],
            "structured_prompts": [
                {
                    "prompt_id": prompt.get("prompt_id"),
                    "variations": [var.get("id") for var in prompt.get("variations", [])]
                }
                for prompt in test_case_data.get("structured_prompts", [])
            ],
        }
        parameters_jsonb = json.dumps(parameters)

        # Description includes the file name
        description = f"Test run using {file_name}"

        # Insert test run record into the database
        cursor.execute("""
            INSERT INTO test_runs (description, model_used, parameters, cost)
            VALUES (%s, %s, %s, %s)
            RETURNING test_run_id;
        """, (description, model_name, parameters_jsonb, 0))  # Cost is 0 for now
        test_run_id = cursor.fetchone()[0]

        logger.info(f"[PG db_utils] Created new test_run_id: {test_run_id}")
        return test_run_id
    except Exception as e:
        logger.error(f"Error creating test_run_id: {e}")
        raise

def fetch_prompts(logger, cursor, test_cases=None, default_detail_levels=["minimal"]):
    """
    Fetch prompts and variations from the database or process JSON test cases.

    Args:
        logger: Logger instance for logging.
        cursor: Database cursor.
        test_cases (dict, optional): Dictionary containing JSON test cases with `prompt_id`, `variations`, and `detail_level`.
        default_detail_levels (list, optional): Default detail levels to use if missing from JSON.

    Returns:
        dict: Dictionary of prompts and variations with detail levels.
    """
    prompts = {"freeform_prompts": [], "structured_prompts": []}

    if test_cases:
        logger.info("Processing JSON test cases.")
        # Extract the detail level from the test cases or use the default
        detail_levels = test_cases.get("detail_level", default_detail_levels)
        if isinstance(detail_levels, str):
            detail_levels = [detail_levels]  # Ensure it's always a list
        logger.debug(f"[fetch_prompts] Using detail levels: {detail_levels}")

        # Process freeform prompts
        for freeform_prompt in test_cases.get("freeform_prompts", []):
            prompt_id = freeform_prompt.get("prompt_id")
            if not prompt_id:
                logger.warning(f"[fetch_prompts] Freeform prompt missing 'prompt_id'. Skipping.")
                continue
            prompts["freeform_prompts"].append({
                "prompt_id": prompt_id,
                "detail_levels": detail_levels,  # Attach all resolved detail levels
            })

        # Process structured prompts
        for structured_prompt in test_cases.get("structured_prompts", []):
            prompt_id = structured_prompt.get("prompt_id")
            if not prompt_id:
                logger.warning(f"[fetch_prompts] Structured prompt missing 'prompt_id'. Skipping.")
                continue
            variations = structured_prompt.get("variations", [])
            prompts["structured_prompts"].append({
                "prompt_id": prompt_id,
                "variations": variations,
                "detail_levels": detail_levels,  # Attach all resolved detail levels
            })

        logger.info(f"[PG db_utils] Processed {len(prompts['freeform_prompts'])} freeform prompts and {len(prompts['structured_prompts'])} structured prompts.")
        return prompts

    raise ValueError("[PG db_utils] `test_cases` must be provided as a dictionary.")