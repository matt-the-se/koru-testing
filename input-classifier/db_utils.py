import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(base_path)
import psycopg2
from psycopg2 import pool
import json
from config import DB_CONFIG, input_classifier_logger as logger

# Initialize connection pool
connection_pool = pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    **DB_CONFIG
)

def validate_connection(conn):
    """
    Validate a database connection and reconnect if closed.
    """
    try:
        if conn.closed:
            conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        raise Exception(f"Error validating/reconnecting database connection: {e}")

def fetch_test_run_inputs(test_run_id, conn):
    """
    Fetch all inputs for a specific test run from the database.
    """
    query = """
    SELECT 
    pi.input_id, 
    pi.extracted_themes, 
    pi.response_text,
    p.prompt_theme AS probable_theme
    FROM persona_inputs pi
    LEFT JOIN prompts p ON pi.prompt_id = p.prompt_id
    WHERE pi.test_run_id = %s;
    """
    try:
        with conn.cursor() as cursor:
            logger.debug(f"[IC db_utils] preparing to fetch inputs for test_run_id {test_run_id}...")
            cursor.execute(query, (test_run_id,))
            inputs = cursor.fetchall()

        validated_inputs = []
        for input_row in inputs:
            input_id, extracted_themes, response_text, probable_theme = input_row

            # Validate extracted_themes
            try:
                if isinstance(extracted_themes, str):
                    extracted_themes = json.loads(extracted_themes)

                if "chunks" not in extracted_themes or not isinstance(extracted_themes["chunks"], list):
                    logger.warning(f"[IC db_utils] Skipping input_id {input_id} due to invalid 'extracted_themes'.")
                    continue

            except json.JSONDecodeError:
                logger.error(f"[IC db_utils] Malformed JSON in 'extracted_themes' for input_id {input_id}.")
                continue  # Skip malformed inputs

            validated_inputs.append((input_id, extracted_themes, response_text, probable_theme))

        return validated_inputs

    except Exception as e:
        logger.error(f"[IC db_utils] Error fetching inputs for test_run_id {test_run_id}: {e}")
        raise Exception(f"Error fetching inputs for test_run_id {test_run_id}: {e}")
    
def update_extracted_theme_count(input_id, theme_frequencies, conn):
    """
    Update the extracted_theme_count column in the database as JSONB.
    """
    query = """
    UPDATE persona_inputs
    SET extracted_theme_count = %s::jsonb
    WHERE input_id = %s;
    """
    try:
        with conn.cursor() as cursor:
            logger.debug(f"[IC db_utils] Preparing to update extracted_theme_count for input_id {input_id}. Data: {theme_frequencies}")
            cursor.execute(query, (json.dumps(theme_frequencies), input_id))
            conn.commit()
            logger.debug(f"[IC db_utils] Successfully updated extracted_theme_count for input_id {input_id}. Data: {theme_frequencies}")
    except Exception as e:
        logger.error(f"[IC db_utils] Error updating extracted_theme_count for input_id {input_id}: {e}")
        conn.rollback()

def update_response_stats(input_id, response_stats, conn):
    """
    Update the response_stats column in the database.
    """
    query = """
    UPDATE persona_inputs
    SET response_stats = %s::jsonb
    WHERE input_id = %s;
    """
    try:
        with conn.cursor() as cursor:
            logger.debug(f"[IC db_utils] Preparing to update response_stats for input_id {input_id}. Data: {response_stats}")
            cursor.execute(query, (json.dumps(response_stats), input_id))
            conn.commit()
            logger.debug(f"[IC db_utils] Successfully updated response_stats for input_id {input_id}. Data: {response_stats}")
    except Exception as e:
        logger.error(f"[IC db_utils] Error updating response_stats for input_id {input_id}: {e}")
        conn.rollback()

def update_extracted_themes(input_id, extracted_themes, conn):
    """
    Update the extracted_themes column in the database.
    """
    query = """
    UPDATE persona_inputs
    SET extracted_themes = %s::jsonb
    WHERE input_id = %s;
    """
    try:
        with conn.cursor() as cursor:
            logger.debug(f"[IC db_utils] Preparing to update extracted_themes for input_id {input_id}. Data: {extracted_themes}")
            cursor.execute(query, (json.dumps(extracted_themes), input_id))
            conn.commit()
            logger.debug(f"[IC db_utils] Successfully updated extracted_themes for input_id {input_id}. Data: {extracted_themes}")
    except Exception as e:
        logger.error(f"[IC db_utils] Error updating extracted_themes for input_id {input_id}: {e}")
        conn.rollback()

def update_confidence(input_id, extracted_themes, conn):
    """
    Update the confidence column in the database with chunk-level and response-level themes and scores.
    """
    query = """
    UPDATE persona_inputs
    SET confidence = %s::jsonb
    WHERE input_id = %s;
    """
    try:
        # Extract response-level confidence
        response_confidence = extracted_themes.get("response_text", {}).get("confidence", {})
        response_themes = extracted_themes.get("response_text", {}).get("response_themes", [])
        primary_response_theme = response_themes[0] if response_themes else None
        primary_response_score = response_confidence.get(primary_response_theme, None)

        # Extract chunk-level confidence
        chunk_confidences = []
        for chunk in extracted_themes.get("chunks", []):
            chunk_confidences.append({
                "chunk_id": chunk.get("chunk_id"),
                "chunk_text": chunk.get("chunk_text", "")[:50],  # Truncated for brevity
                "chunk_themes": chunk.get("chunk_themes", []),
                "confidence": chunk.get("confidence", {})
            })

        # Create confidence data structure
        confidence_data = {
            "response": {
                "theme": primary_response_theme,
                "score": primary_response_score,
            },
            "chunks": chunk_confidences
        }

        # Update the database
        with conn.cursor() as cursor:
            cursor.execute(query, (json.dumps(confidence_data), input_id))
            conn.commit()
            logger.debug(f"[IC db_utils] Successfully updated confidence for input_id {input_id}. Data: {confidence_data}")
    except Exception as e:
        logger.error(f"[IC db_utils] Error updating confidence for input_id {input_id}: {e}")
        conn.rollback()