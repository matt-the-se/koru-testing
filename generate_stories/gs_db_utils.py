import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)

import psycopg2
from psycopg2.extras import RealDictCursor
from collections import Counter
from config import DB_CONFIG, generate_stories_logger as logger
from typing import List, Dict

def fetch_persona_data(persona_id: int, test_run_id: int) -> List[Dict]:
    """
    Fetch data for a specific persona and/or test run from the database.

    Args:
        persona_id (int): The ID of the persona to fetch data for.
        test_run_id (int): The ID of the test run to filter data.

    Returns:
        dict: A dictionary containing persona foundation details and a list of inputs with probable themes.
    """
    logger.info(f"Fetching persona data for persona_id={persona_id}, test_run_id={test_run_id}")
    
    try:
        # Connect to the database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Execute the query
        cur.execute("""
            SELECT 
                ps.foundation,
                pi.test_run_id,
                pi.input_id,
                pi.persona_id,
                pi.prompt_id,
                pi.response_text,
                pi.extracted_themes,
                pi.extracted_theme_count,
                pi.response_stats,
                p.prompt_theme
            FROM personas ps
            LEFT JOIN persona_inputs pi ON ps.persona_id = pi.persona_id  
            LEFT JOIN prompts p ON pi.prompt_id = p.prompt_id
            WHERE ps.persona_id = %s AND pi.test_run_id = %s
        """, (persona_id, test_run_id))
        
        results = cur.fetchall()
        logger.info(f"Found {len(results)} rows of persona data")
        
        if not results:
            logger.warning(f"No data found for persona_id: {persona_id} and test_run_id: {test_run_id}")
            return None
            
        foundation = results[0]['foundation']  # Shared across all rows for the persona
        test_run = results[0]['test_run_id']
        inputs = [
            {
                "input_id": row["input_id"],
                "prompt_id": row["prompt_id"],
                "response_text": row["response_text"],
                "extracted_themes": row["extracted_themes"],
                "extracted_theme_count": row["extracted_theme_count"],
                "response_stats": row["response_stats"],
                "prompt_theme": row["prompt_theme"]
            }
            for row in results
        ]
        return {"foundation": foundation, "test_run_id": test_run, "inputs": inputs}

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

def pull_input_stats(test_run_id, detail_level=None):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Build the query dynamically
        query = """
            SELECT extracted_themes
            FROM persona_inputs
            WHERE test_run_id = %s AND extracted_themes IS NOT NULL
        """
        params = [test_run_id]

        if detail_level:
            query += " AND detail_level = %s"
            params.append(detail_level)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            print("No rows matched the query. Check test_run_id and detail_level.")
            return None

        # Initialize counters and lists
        chunk_confidences = []
        response_confidences = []
        theme_totals = Counter()
        theme_confidences = {}

        # Process each row
        for row in rows:
            extracted_themes = row[0]

            # Count themes and track confidences from chunks
            if 'chunks' in extracted_themes:
                for chunk in extracted_themes['chunks']:
                    if 'confidence' in chunk:
                        for theme, score in chunk['confidence'].items():
                            theme_confidences.setdefault(theme, []).append(score)
                        theme_totals.update(chunk['confidence'].keys())
                        chunk_confidences.extend(chunk['confidence'].values())

            # Count themes and track confidences from response text
            if 'response_text' in extracted_themes and 'confidence' in extracted_themes['response_text']:
                for theme, score in extracted_themes['response_text']['confidence'].items():
                    theme_confidences.setdefault(theme, []).append(score)
                theme_totals.update(extracted_themes['response_text']['confidence'].keys())
                response_confidences.extend(extracted_themes['response_text']['confidence'].values())

        # Fetch test run stats
        test_run_stats = get_test_run_stats(test_run_id, cursor)

        # Close the connection
        cursor.close()
        conn.close()

        return {
            "test_run_stats": test_run_stats,
            "chunk_confidences": chunk_confidences,
            "response_confidences": response_confidences,
            "theme_totals": theme_totals,
            "theme_confidences": theme_confidences,
        }

    except Exception as e:
        print(f"Error: {e}")
        return None
    
def get_test_run_stats(test_run_id, cursor):
    stats = {}

    # Test case JSON
    cursor.execute("SELECT description FROM test_runs WHERE test_run_id = %s", (test_run_id,))
    stats['Test Case JSON'] = cursor.fetchone()[0]

    # Number of personas
    cursor.execute("SELECT COUNT(persona_id) FROM personas WHERE test_run_id = %s", (test_run_id,))
    stats['Personas'] = cursor.fetchone()[0]

    # Freeform and structured prompts
    cursor.execute("""
        SELECT p.prompt_type, COUNT(DISTINCT pi.prompt_id) AS count
        FROM persona_inputs pi
        JOIN prompts p ON pi.prompt_id = p.prompt_id
        WHERE pi.test_run_id = %s
        GROUP BY p.prompt_type;
    """, (test_run_id,))
    prompt_counts = dict(cursor.fetchall())
    stats['Freeform Prompts'] = prompt_counts.get('freeform_prompts', 0)
    stats['Structured Prompts'] = prompt_counts.get('structured_prompts', 0)

    # Structured variations
    cursor.execute("SELECT COUNT(DISTINCT variation_id) FROM persona_inputs WHERE test_run_id = %s", (test_run_id,))
    stats['Structured Variations'] = cursor.fetchone()[0]

    # Responses generated
    cursor.execute("SELECT COUNT(response_text) FROM persona_inputs WHERE test_run_id = %s", (test_run_id,))
    stats['Responses'] = cursor.fetchone()[0]

    # Total chunks
    cursor.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT jsonb_array_elements((extracted_themes->'chunks')::jsonb) AS chunk
            FROM persona_inputs
            WHERE test_run_id = %s AND extracted_themes IS NOT NULL
        ) chunks
    """, (test_run_id,))
    stats['Total Chunks'] = cursor.fetchone()[0]

    # Average chunks per response
    cursor.execute("""
        SELECT AVG(chunk_count)
        FROM (
            SELECT jsonb_array_length((extracted_themes->'chunks')::jsonb) AS chunk_count
            FROM persona_inputs
            WHERE test_run_id = %s AND extracted_themes IS NOT NULL
        ) chunk_counts
    """, (test_run_id,))
    stats['Avg Chunks per Response'] = round(cursor.fetchone()[0], 2)

    return stats