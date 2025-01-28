import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)
import psycopg2
from config import DB_CONFIG
from collections import Counter
import numpy as np


def pull_clarity_score_inputs(logger, test_run_id):
    """
    Extracts data required for clarity score calculation from persona_inputs.
    Args:
        test_run_id (int): The test run ID to process.
    Returns:
        dict: Data required for clarity score computation, grouped by persona_id.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Query persona_inputs for the test run
        logger.info(f"[Pull Clarity Inputs] Querying persona_inputs for test_run_id: {test_run_id}")
        cursor.execute("""
            SELECT persona_id, extracted_themes, keyword_matches
            FROM persona_inputs
            WHERE test_run_id = %s AND extracted_themes IS NOT NULL
        """, (test_run_id,))
        rows = cursor.fetchall()

        if not rows:
            logger.warning(f"[Pull Clarity Inputs] No rows found for test_run_id {test_run_id}.")
            print(f"No rows found for test_run_id {test_run_id}.")
            return None

        # Initialize data structures
        persona_data = {}

        logger.info(f"[Pull Clarity Inputs] Processing {len(rows)} rows for test_run_id {test_run_id}.")

        # Process each row
        for row in rows:
            persona_id, extracted_themes, keyword_data = row

            if persona_id not in persona_data:
                persona_data[persona_id] = {
                    "aggregate_themes": Counter(),
                    "complete_response_themes": Counter(),
                    "probable_theme": None,
                    "chunk_scores": [],
                    "keyword_matches": Counter(),
                    "foundation_complete": True,  # Placeholder
                    "completeness_bucket": 0.0,
                }

            # Aggregate chunk themes and confidences
            if 'chunks' in extracted_themes:
                for chunk in extracted_themes['chunks']:
                    if 'confidence' in chunk:
                        for theme, score in chunk['confidence'].items():
                            persona_data[persona_id]["aggregate_themes"][theme] += score
                            persona_data[persona_id]["chunk_scores"].append((theme, score))

            # Process complete response themes
            if 'response_text' in extracted_themes and 'confidence' in extracted_themes['response_text']:
                for theme, score in extracted_themes['response_text']['confidence'].items():
                    persona_data[persona_id]["complete_response_themes"][theme] += score

                # Probable theme
                if 'top_theme' in extracted_themes['response_text']:
                    top_theme = extracted_themes['response_text']['top_theme']
                    top_confidence = extracted_themes['response_text'].get('top_confidence', 0.0)
                    persona_data[persona_id]["probable_theme"] = (top_theme, top_confidence)

            # Keyword matches
            if keyword_data:
                for theme, data in keyword_data.items():
                    match_count = len(data.get("matches", []))
                    persona_data[persona_id]["keyword_matches"][theme] += match_count

            # Completeness bucket
            if 'completeness_bucket' in extracted_themes:
                persona_data[persona_id]["completeness_bucket"] += extracted_themes['completeness_bucket']

        # Normalize aggregate and complete response themes per persona
        for persona_id, data in persona_data.items():
            # Normalize aggregate themes
            total_aggregate_score = sum(data["aggregate_themes"].values())
            if total_aggregate_score > 0:
                for theme in data["aggregate_themes"]:
                    data["aggregate_themes"][theme] /= total_aggregate_score

            # Normalize complete response themes
            total_response_score = sum(data["complete_response_themes"].values())
            if total_response_score > 0:
                for theme in data["complete_response_themes"]:
                    data["complete_response_themes"][theme] /= total_response_score

        # Debug: Log final data structures
        logger.info(f"[Pull Clarity Inputs] Final persona_data: {persona_data}")

        # Close the connection
        cursor.close()
        conn.close()

        return persona_data

    except Exception as e:
        print(f"Error in pull_clarity_score_inputs: {e}")
        return None

def get_score_distribution(scores, bin_width=0.05):
    bins = np.arange(0.3, 0.8, bin_width)
    histogram = Counter(np.digitize(scores, bins))
    return {f"{bins[i]:.2f}-{bins[i+1]:.2f}": histogram[i+1] for i in range(len(bins) - 1)}


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
            SELECT jsonb_array_length(extracted_themes->'chunks') AS chunk_count
            FROM persona_inputs
            WHERE test_run_id = %s AND extracted_themes IS NOT NULL
        ) chunk_counts
    """, (test_run_id,))
    stats['Avg Chunks per Response'] = round(cursor.fetchone()[0], 2)

    return stats


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