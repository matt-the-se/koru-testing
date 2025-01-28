import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)
import argparse
import json
from sentence_transformers import SentenceTransformer
from config import SYNONYM_LIBRARY_PATH, input_classifier_logger as logger
from db_utils import connection_pool, update_extracted_theme_count, update_response_stats, fetch_test_run_inputs, update_extracted_themes, update_confidence
from synonym_utils import load_synonym_library, generate_theme_embeddings
from post_processing import classify_chunk, aggregate_themes, calculate_response_stats, calculate_theme_frequencies


logger.info("[input_classifier] Starting...")

# Load the SentenceTransformer model for text embeddings
sbert_model = SentenceTransformer('all-MiniLM-L6-v2')

def load_synonym_library(file_path):
    """
    Load the synonym library from a JSON file.
    This file maps themes to their associated synonyms.
    """
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"[input_classifier] Error loading synonym library: {e}")
        return {}

# Load the synonym library into memory
SYNONYM_LIBRARY = load_synonym_library(SYNONYM_LIBRARY_PATH)

# Load theme embeddings
THEME_EMBEDDINGS = generate_theme_embeddings(SYNONYM_LIBRARY, sbert_model)

def process_input(input_id, extracted_themes, response_text, test_run_id, probable_theme, conn):
    """
    Main function to process an input for classification.
    """
    try:
        logger.info(f"[input_classifier] Processing input_id {input_id} for test_run_id {test_run_id}.")

        # Extract and validate probable_theme
        probable_theme = extract_probable_theme(probable_theme, input_id)

        # Validate and classify chunks
        classified_chunks = classify_chunks(extracted_themes, probable_theme, input_id, test_run_id)

        if not classified_chunks:
            logger.error(f"[input_classifier] No valid chunks processed for input_id {input_id}. Skipping input.")
            return

        # Append chunk classifications to extracted_themes
        extracted_themes["chunks"] = [
            {
                "chunk_id": chunk["chunk_id"],
                "chunk_text": chunk["chunk_text"],
                "chunk_themes": chunk["chunk_themes"],
                "confidence": {theme: float(score) for theme, score in chunk["confidence"].items()},
            }
            for chunk in classified_chunks
        ]
        
        # Classify the entire response_text as standalone
        response_themes, response_matching_scores = classify_chunk(
            response_text, probable_theme, sbert_model, THEME_EMBEDDINGS, logger
        )
        logger.info(f"[input_classifier] Response text themes for input_id {input_id}: {response_themes}")

        # Append response_text classification to extracted_themes
        logger.debug(f"[input_classifier!] response_matching_scores for input_id {input_id}: {response_matching_scores}")
        try:
            if isinstance(response_matching_scores, dict):
                response_matching_scores = list(response_matching_scores.items())
            
            # Extract top response theme and score
            top_response_theme = response_themes[0] if response_themes else None
            top_response_score = response_matching_scores[0][1] if response_matching_scores else None

            extracted_themes["response_text"] = {
                "response_themes": response_themes,
                "confidence": {theme: float(score) for theme, score in response_matching_scores},
                "top_theme": top_response_theme,
                "top_confidence": float(top_response_score) if top_response_score else None
            }
        except ValueError as e:
            logger.error(f"[input_classifier] Failed to process response_matching_scores for input_id {input_id}: {e}")
            extracted_themes["response_text"] = {
                "response_themes": response_themes,
                "confidence": {},
                "top_theme": None,
                "top_confidence": None
            }

        # Update the extracted_themes column in the database
        update_extracted_themes(input_id, extracted_themes, conn)

        # Aggregate themes (excluding response_text classification)
        aggregated_themes = aggregate_themes(classified_chunks, SYNONYM_LIBRARY)
        logger.info(f"[input_classifier] Aggregated themes for input_id {input_id}: {aggregated_themes['aggregated']}.")

        # Calculate theme frequencies
        theme_frequencies = calculate_theme_frequencies(extracted_themes, probable_theme)
        logger.info(f"[input_classifier] Theme frequencies for input_id {input_id}: {theme_frequencies}")

        # Update extracted theme count in DB
        update_extracted_theme_count(input_id, theme_frequencies, conn)

        # Prepare confidence data
        chunk_confidence = {
            "chunk": [
                {
                    "chunk_id": chunk["chunk_id"],
                    "chunk_themes": chunk["chunk_themes"],
                    "confidence": chunk["confidence"],
                }
                for chunk in classified_chunks
            ],
            "response_text": {
                "themes": extracted_themes["response_text"]["response_themes"],
                "confidence": extracted_themes["response_text"]["confidence"],
                "top_theme": extracted_themes["response_text"]["top_theme"],
                "top_confidence": extracted_themes["response_text"]["top_confidence"]
            }
        }
        logger.debug(f"[input_classifier!!] Prepared chunk_confidence for input_id {input_id}: {json.dumps(chunk_confidence, indent=2)}")

        # Update confidence column in the database
        update_confidence(input_id, chunk_confidence, conn)

        # Calculate and update response stats
        response_stats = calculate_response_stats(response_text, theme_frequencies, probable_theme)
        logger.info(f"[input_classifier] Response stats for input_id {input_id}: {response_stats}")
        update_response_stats(input_id, response_stats, conn)

    except Exception as e:
        logger.error(f"[input_classifier] Error processing input_id {input_id}: {e}")


def extract_probable_theme(probable_theme, input_id):
    if probable_theme == "Not Used":
        logger.debug(f"[input_classifier] Freeform prompt detected for input_id {input_id}.")
        return "Not Used"

    if isinstance(probable_theme, dict):
        probable_theme = list(probable_theme.keys())[0]
        logger.debug(f"[input_classifier] Extracted probable_theme from dict: {probable_theme}")
    elif isinstance(probable_theme, str):
        try:
            probable_theme = list(json.loads(probable_theme).keys())[0]
            logger.debug(f"[input_classifier] Extracted probable_theme: {probable_theme}")
        except Exception as e:
            logger.error(f"[input_classifier] Error parsing probable_theme for input_id {input_id}: {e}")
            probable_theme = "Not Used"
    elif isinstance(probable_theme, list):  # Handle list case
        logger.error(f"[input_classifier] Unexpected probable_theme type: list. Using fallback 'Not Used'.")
        probable_theme = "Not Used"
    else:
        logger.error(f"[input_classifier] Invalid probable_theme type for input_id {input_id}: {type(probable_theme)}")
        probable_theme = "Not Used"

    return probable_theme


def classify_chunks(extracted_themes, probable_theme, input_id, test_run_id):
    """
    Classify each chunk in the extracted themes using classify_chunk.
    """
    # Validate and retrieve chunks
    chunks = extracted_themes.get("chunks")
    logger.debug(f"[input_classifier] Retrieved chunks: {chunks}")
    if not chunks or not isinstance(chunks, list):
        logger.error(
            f"[input_classifier] No chunks found in extracted themes for input_id {input_id}. "
            f"Have you run the input chunker for test run {test_run_id}?"
        )
        raise ValueError("Missing chunks in extracted_themes.")

    # Initialize classified_chunks list
    classified_chunks = []
    processed_chunks = set()  # Track processed (input_id, chunk_id) pairs

    # Process each chunk
    for chunk in chunks:
        # Composite key to handle duplicate chunk_ids across input_ids
        key = (input_id, chunk.get("chunk_id", "unknown"))

        # Skip already processed chunks
        if key in processed_chunks:
            logger.warning(f"[input_classifier] Skipping duplicate chunk: {key}")
            continue
        processed_chunks.add(key)

        # Ensure the chunk is a valid dictionary
        if not isinstance(chunk, dict):
            logger.warning(f"[input_classifier] Invalid chunk type: {type(chunk)}. Skipping chunk: {chunk}")
            continue

        # Ensure 'chunk_text' is present
        if "chunk_text" not in chunk:
            logger.warning(f"[input_classifier] Missing 'chunk_text' in chunk. Skipping chunk: {chunk}")
            continue

        try:
            # Call classify_chunk for each chunk
            logger.debug(f"[input_classifier] Processing chunk_id {chunk.get('chunk_id', 'unknown')} for input_id {input_id}")
            chunk_themes, matching_scores = classify_chunk(
                chunk["chunk_text"], probable_theme, sbert_model, THEME_EMBEDDINGS, logger
            )
        except Exception as e:
            logger.error(f"[input_classifier] Error in classify_chunk: {e}")
            chunk_themes, matching_scores = [], {}

        # Append classified chunk
        classified_chunks.append({
            "chunk_id": chunk.get("chunk_id", "unknown"),
            "chunk_text": chunk["chunk_text"],
            "chunk_themes": chunk_themes,
            "confidence": matching_scores,
        })

    if not classified_chunks:
        logger.error(f"[input_classifier] No valid chunks classified for input_id {input_id}.")
    else:
        logger.info(f"[input_classifier] Successfully classified {len(classified_chunks)} chunks for input_id {input_id}.")

    return classified_chunks

    # Handle cases where no valid chunks were processed
    if not classified_chunks:
        logger.error(f"[input_classifier] No valid chunks classified for input_id {input_id}.")
    else:
        logger.info(f"[input_classifier] Successfully classified {len(classified_chunks)} chunks for input_id {input_id}.")

    return classified_chunks

def process_test_run(test_run_id):
    """
    Fetch and process all inputs for a specific test run.
    """
    conn = connection_pool.getconn()
    try:
        logger.info(f"[input_classifier] Fetching input chunks for {test_run_id}...")
        inputs = fetch_test_run_inputs(test_run_id, conn)
        logger.info(f"[input_classifier] Fetched {len(inputs)} inputs for test_run_id {test_run_id}")

        for input_row in inputs:
            # Unpack the input row
            input_id, extracted_themes, response_text, probable_theme = input_row

            # Ensure extracted_themes is parsed correctly
            try:
                if isinstance(extracted_themes, str):
                    extracted_themes = json.loads(extracted_themes)
            except json.JSONDecodeError as e:
                logger.error(f"[input_classifier] Failed to parse extracted_themes for input_id {input_id}: {e}")
                continue  # Skip this input if malformed

            # Process the input
            process_input(input_id, extracted_themes, response_text, test_run_id, probable_theme, conn)

    except Exception as e:
        logger.error(f"[input_classifier] Error processing inputs for test_run_id {test_run_id}: {e}")
    finally:
        connection_pool.putconn(conn)
        logger.info(f"[input_classifier] Database connection returned for test_run {test_run_id}.")

    logger.info(f"[input_classifier] Script completed for test run {test_run_id}")

def main():
    """
    Main entry point: Parse arguments and start processing the test run.
    """
    parser = argparse.ArgumentParser(description="Classify pre-chunked persona inputs for a specific test run ID.")
    parser.add_argument("test_run_id", type=int, help="The ID of the test run to process.")
    args = parser.parse_args()
    process_test_run(args.test_run_id)

if __name__ == "__main__":
    main()