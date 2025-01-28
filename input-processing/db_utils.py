import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)
import psycopg2
import json
from config import DB_CONFIG, input_processing_logger as logger


conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

#input chunker
def get_inputs_for_test_run(logger, test_run_id):
    """
    Fetch inputs for a specific test run.
    """
    query = """
    SELECT input_id, response_text
    FROM persona_inputs
    WHERE test_run_id = %s;
    """
    try:
        cursor.execute(query, (test_run_id,))
        inputs = cursor.fetchall()
        logger.info(f"[IP db_utils] Fetched {len(inputs)} inputs for test_run_id {test_run_id}")
        return inputs
    except Exception as e:
        logger.error(f"[IP db_utils] Error fetching inputs for test_run_id {test_run_id}: {e}")

# input chunker
def update_chunks_in_db(logger, input_id, chunks):
    """
    Update the persona_inputs table with chunked data.
    """
    query = """
    UPDATE persona_inputs
    SET extracted_themes = %s
    WHERE input_id = %s;
    """
    try:
        cursor.execute(query, (json.dumps({"chunks": chunks}), input_id))
        conn.commit()
        logger.info(f"[IP db_utils] Updated input_id {input_id} with chunk data.")
    except Exception as e:
        logger.error(f"[IP db_utils] Error updating persona_inputs for input_id {input_id}: {e}")
        conn.rollback()

# keyword matcher
def fetch_tags_and_responses(logger, test_run_id):
    """
    Fetch tags and response_text from persona_inputs for a specific test_run_id.
    Args:
        logger: Logger instance.
        test_run_id (int): The test_run_id to filter responses.
    Returns:
        tags (dict): Theme-wise tag details.
        responses (list): List of persona_id, input_id, response_text, and test_run_id.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Fetch tags
        cursor.execute("SELECT theme, tags FROM tags")
        tag_data = cursor.fetchall()
        tags = {theme: tag_info for theme, tag_info in tag_data}
        logger.debug(f"[IC db_utils] Tags fetched: {tags}")

        # Fetch responses for the given test_run_id
        cursor.execute("""
        SELECT persona_id, input_id, response_text, test_run_id
        FROM persona_inputs
        WHERE test_run_id = %s
    """, (test_run_id,))
        responses = cursor.fetchall()
        logger.debug(f"[IC db_utils] Responses fetched for test_run_id {test_run_id}: {responses}")

        return tags, responses
    except Exception as e:
        logger.exception(f"[IC db_utils] Error during fetch_tags_and_responses for test_run_id {test_run_id}: {e}")
        return {}, []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

#keyword matcher
def insert_keyword_match(logger, persona_id, input_id, matches):
    """
    Updates the keyword_matches column in the persona_inputs table.
    Args:
        logger: Logger instance.
        persona_id (int): The persona ID.
        input_id (int): The input ID.
        matches (dict): The keyword matches to store, keyed by theme.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Fetch existing matches
        cursor.execute("""
            SELECT keyword_matches FROM persona_inputs
            WHERE persona_id = %s AND input_id = %s
        """, (persona_id, input_id))
        existing_matches = cursor.fetchone()[0] or {}

        # Merge new matches with existing ones
        for theme, new_match_data in matches.items():
            if theme not in existing_matches:
                existing_matches[theme] = new_match_data
            else:
                # Merge matches, avoiding duplicates
                existing_themes = existing_matches[theme]["matches"]
                new_matches = new_match_data["matches"]
                combined_matches = {m["keyword"]: m for m in (existing_themes + new_matches)}.values()
                existing_matches[theme]["matches"] = list(combined_matches)

        # Update the database
        cursor.execute("""
            UPDATE persona_inputs
            SET keyword_matches = %s
            WHERE persona_id = %s AND input_id = %s
        """, (json.dumps(existing_matches), persona_id, input_id))

        conn.commit()
        logger.debug(f"[IC db_utils] Updated keyword_matches for input_id {input_id}: {existing_matches}")
    except Exception as e:
        logger.exception(f"[IC db_utils] Error during insert_keyword_match for input_id {input_id}: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

#keyword Matcher
def reset_keyword_matches(logger, test_run_id):
    """
    Clears the keyword_matches column for a given test_run_id.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE persona_inputs
            SET keyword_matches = NULL
            WHERE test_run_id = %s
        """, (test_run_id,))
        conn.commit()
        logger.info(f"[IC db_utils] Cleared keyword_matches for test_run_id: {test_run_id}")
    except Exception as e:
        logger.exception(f"[IC db_utils] Error during reset_keyword_matches for test_run_id {test_run_id}: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

#clarity score calc

def fetch_clarity_data(logger, test_run_id):
    """
    Fetches keyword_matches and word_count for inputs in a given test_run_id.
    Args:
        logger: Logger instance for logging.
        test_run_id (int): The test run ID to filter inputs.
    Returns:
        dict: A dictionary mapping persona_id and input_id to theme-level data.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Fetch keyword_matches and word_count
        cursor.execute("""
            SELECT 
                persona_id, 
                input_id, 
                keyword_matches, 
                response_stats
            FROM persona_inputs
            WHERE test_run_id = %s
        """, (test_run_id,))
        rows = cursor.fetchall()

        clarity_data = {}
        for persona_id, input_id, keyword_matches, response_stats in rows:
            # Parse JSON fields
            keyword_matches = keyword_matches or {}
            response_stats = json.loads(response_stats) if response_stats else {}

            # Extract word_count
            word_count = response_stats.get("word_count", 0)

            # Map data
            clarity_data[(persona_id, input_id)] = {
                "keyword_matches": keyword_matches,
                "word_count": word_count,
            }

        logger.debug(f"[IC db_utils] Fetched clarity data for test_run_id {test_run_id}: {clarity_data}")
        return clarity_data
    except Exception as e:
        logger.exception(f"[IC db_utils] Error fetching clarity data for test_run_id {test_run_id}: {e}")
        return {}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def save_clarity_scores(logger, persona_id, clarity_scores):
    """
    Save clarity scores to the database for a specific persona.

    Args:
        persona_id (int): The ID of the persona.
        clarity_scores (dict): The clarity score breakdown to store.
    """
    query = """
        UPDATE personas
        SET clarity_scores = %s
        WHERE persona_id = %s;
    """
    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Execute the query
        cur.execute(query, (json.dumps(clarity_scores), persona_id))
        conn.commit()

        logger.info(f"[IC db_utils] Clarity scores saved for persona_id={persona_id}")
    except psycopg2.Error as e:
        logger.error(f"[IC db_utils] Failed to save clarity scores for persona_id={persona_id}: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()