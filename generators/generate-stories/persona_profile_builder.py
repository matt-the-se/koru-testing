import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(base_path)
import json
import psycopg2
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from collections import Counter
from config import DB_CONFIG, generate_stories_logger as logger
from db_utils import fetch_persona_data, pull_input_stats

# Check if VADER lexicon is already installed before downloading
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

# Initialize sentiment analyzer
sia = SentimentIntensityAnalyzer()


def calculate_passion_score(response_text, extracted_themes):
    """
    Calculate a passion score based on emotional words, repetition, length, and sentiment.
    
    Args:
        response_text (str): User-provided response.
        extracted_themes (dict): Extracted theme confidences from response.

    Returns:
        float: Computed passion score.
    """
    passion_keywords = {"love", "dream", "joy", "fulfilled", "passionate", "excited", "obsessed", "deeply"}
    word_count = len(response_text.split())
    passion_count = sum(1 for word in response_text.lower().split() if word in passion_keywords)
    sentiment_score = sia.polarity_scores(response_text)['pos']  # Positive sentiment emphasis
    
    repetition_weight = sum(extracted_themes.values())  # More repeated themes → higher weight
    detail_weight = word_count / 50  # Assume ~50 words = meaningful detail
    passion_multiplier = 1 + (passion_count / max(word_count, 1))  # Passion keyword scaling
    
    return (sentiment_score * 2) + repetition_weight + detail_weight + passion_multiplier


def store_passion_scores(persona_id, test_run_id, inputs):
    """
    Store computed passion scores in the database as a single JSON object.

    Args:
        persona_id (int): The persona ID.
        test_run_id (int): The test run ID.
        inputs (list): List of persona input dictionaries.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Create a dictionary of passion scores with input_id as keys
        passion_scores_dict = {
            str(input_data['input_id']): calculate_passion_score(
                input_data['response_text'], 
                input_data.get('extracted_themes', {}).get('response_text', {}).get('confidence', {})
            )
            for input_data in inputs
        }

        if not passion_scores_dict:
            logger.warning(f"No passion scores generated for persona {persona_id}, skipping DB update.")
            return  # Exit early if there's nothing to store

        # Convert dictionary to JSON
        passion_scores_json = json.dumps(passion_scores_dict)

        # Update the persona's passion_scores column with the JSON object
        cur.execute("""
            UPDATE persona_inputs
            SET passion_scores = %s::jsonb
            WHERE persona_id = %s
        """, (passion_scores_json, persona_id))

        conn.commit()
        
        # Debug: Confirm database update
        logger.info(f"Successfully updated passion_scores for persona {persona_id}")

        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error storing passion scores: {e}")


def build_persona_profile(logger, persona_id, test_run_id):
    """
    Construct a detailed persona profile by aggregating multiple data sources.
    
    Args:
        persona_id (int): The persona ID.
        test_run_id (int): The test run ID.
    
    Returns:
        dict: Aggregated persona profile.
    """
    # Before calling fetch_persona_data, ensure we retrieve the test_run_id if missing
    if test_run_id is None and persona_id is not None:
        # Query the database to get test_run_id
        query = "SELECT test_run_id FROM personas WHERE persona_id = %s;"
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(query, (persona_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            test_run_id = result[0]

    # Fetch raw input data
    persona_data = fetch_persona_data(persona_id, test_run_id)
    if not persona_data:
        logger.warning(f"No persona data found for persona_id={persona_id}, test_run_id={test_run_id}")
        return None
    
    # Pull statistical theme data
    input_stats = pull_input_stats(test_run_id)
    if not input_stats:
        logger.warning(f"No input stats available for test_run_id={test_run_id}")
        return None
    
    # Compute passion scores and store them in DB
    store_passion_scores(persona_id, test_run_id, persona_data['inputs'])
    
    # Extract prioritized themes
    theme_confidences = input_stats['theme_confidences']
    sorted_themes = sorted(theme_confidences.items(), key=lambda x: x[1], reverse=True)
    primary_theme = sorted_themes[0][0] if sorted_themes else None
    secondary_themes = [t[0] for t in sorted_themes[1:3]] if len(sorted_themes) > 1 else []
    
    return {
        "persona_id": persona_id,
        "test_run_id": test_run_id,
        "foundation": persona_data["foundation"],
        "inputs": persona_data["inputs"],
        "theme_confidences": input_stats["theme_confidences"],
        "chunk_confidences": input_stats["chunk_confidences"],
        "response_confidences": input_stats["response_confidences"],
        "theme_totals": input_stats["theme_totals"],
        "passion_scores": {input_data['input_id']: calculate_passion_score(input_data['response_text'], input_data.get('extracted_themes', {}).get('response_text', {}).get('confidence', {})) for input_data in persona_data['inputs']},
        "primary_theme": primary_theme,
        "secondary_themes": secondary_themes
    }

