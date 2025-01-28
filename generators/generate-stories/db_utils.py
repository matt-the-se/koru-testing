import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG, generate_stories_logger as logger

def fetch_persona_data(persona_id, test_run_id):
    """
    Fetch data for a specific persona and test run from the database.

    Args:
        persona_id (int): The ID of the persona to fetch data for.
        test_run_id (int): The ID of the test run to filter data.

    Returns:
        dict: A dictionary containing persona foundation details and a list of inputs with probable themes.
    """
    query = """
        SELECT 
            ps.foundation,
            ps.test_run_id,
            pi.input_id,
            pi.persona_id,
            pi.prompt_id,
            pi.response_text,
            pi.extracted_themes,
            pi.extracted_theme_count,
            pi.response_stats,
            p.prompt_theme
        FROM personas ps
        JOIN persona_inputs pi ON ps.persona_id = pi.persona_id
        JOIN prompts p ON pi.prompt_id = p.prompt_id
        WHERE ps.persona_id = %s AND ps.test_run_id = %s;
    """

    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Execute the query
        cur.execute(query, (persona_id, test_run_id))

        # Fetch all results
        rows = cur.fetchall()

        # Organize data into a structured format
        if rows:
            foundation = rows[0]['foundations']  # Shared across all rows for the persona
            test_run = rows[0]['test_run_id']
            inputs = [
                {
                    "input_id": row["input_id"],
                    "prompt_id": row["prompt_id"],
                    "response_text": row["response_text"],
                    "extracted_themes": row["extracted_themes"],
                    "extracted_theme_count": row["extracted_theme_count"],
                    "response_stats": row["response_stats"],
                    "prompt_theme": row["probable_theme"]
                }
                for row in rows
            ]
            return {"foundation": foundation, "test_run_id": test_run, "inputs": inputs}
        else:
            logger.warning(f"No data found for persona_id: {persona_id} and test_run_id: {test_run_id}")
            return None

    except psycopg2.Error as e:
        logger.error(f"Database error while fetching data for persona_id {persona_id} and test_run_id {test_run_id}: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def fetch_all_personas_in_test_run(test_run_id):
    """
    Fetch data for all personas in a specific test run.

    Args:
        test_run_id (int): The ID of the test run.

    Returns:
        list[dict]: A list of dictionaries containing data for all personas in the test run.
    """
    query = """
        SELECT 
            ps.foundation,
            ps.test_run_id,
            pi.input_id,
            pi.persona_id,
            pi.prompt_id,
            pi.response_text,
            pi.extracted_themes,
            pi.extracted_theme_count,
            pi.response_stats,
            p.prompt_theme
        FROM personas ps
        JOIN persona_inputs pi ON ps.persona_id = pi.persona_id
        JOIN prompts p ON pi.prompt_id = p.prompt_id
        WHERE ps.test_run_id = %s;
    """

    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Execute the query
        cur.execute(query, (test_run_id,))

        # Fetch all results
        rows = cur.fetchall()

        # Organize results by persona
        personas = {}
        for row in rows:
            persona_id = row["persona_id"]
            if persona_id not in personas:
                personas[persona_id] = {
                    "foundation": row["foundation"],
                    "test_run_id": row["test_run_id"],
                    "inputs": []
                }
            # Add persona_id to each input explicitly
            personas[persona_id]["inputs"].append({
                "input_id": row["input_id"],
                "persona_id": row["persona_id"],  # Ensure persona_id is included
                "prompt_id": row["prompt_id"],
                "response_text": row["response_text"],
                "extracted_themes": row["extracted_themes"],
                "extracted_theme_count": row["extracted_theme_count"],
                "response_stats": row["response_stats"],
                "prompt_theme": row["prompt_theme"]
            })

        return list(personas.values())

    except psycopg2.Error as e:
        logger.error(f"Database error while fetching personas for test_run_id {test_run_id}: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()