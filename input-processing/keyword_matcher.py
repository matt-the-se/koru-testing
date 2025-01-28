import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)
import spacy
from config import input_processing_logger as logger
from db_utils import fetch_tags_and_responses, insert_keyword_match, reset_keyword_matches
import argparse

# Load SpaCy for lemmatization
nlp = spacy.load("en_core_web_sm")

def match_keywords(test_run_id, reprocess=False):
    """
    Matches keywords in response_text with tags for a specific test_run_id
    and updates the database.
    Args:
        test_run_id (int): The test_run_id to scope the matching process.
        reprocess (bool): Whether to reprocess all rows by resetting keyword_matches.
    """
    logger.info(f"[KW-match] Starting keyword matching for test_run_id: {test_run_id} (reprocess={reprocess})")

    # Reset keyword_matches if reprocess is True
    if reprocess:
        logger.info(f"[KW-match] Reprocessing enabled. Resetting keyword_matches for test_run_id: {test_run_id}")
        reset_keyword_matches(test_run_id)

    # Fetch tags and responses
    logger.info(f"[KW-match] Fetching tags and responses for test_run_id: {test_run_id}...")
    tags, responses = fetch_tags_and_responses(logger, test_run_id)

    if not responses:
        logger.info(f"[KW-match] No responses found for test_run_id: {test_run_id}. Exiting.")
        return

    logger.info(f"[KW-match] Starting keyword matching process...")
    for persona_id, input_id, response_text, _ in responses:
        doc = nlp(response_text.lower())
        tokens = [token.lemma_ for token in doc]
        raw_tokens = [token.text for token in doc]
        logger.debug(f"[KW-match] Tokens for input_id {input_id}: {tokens}")
        logger.debug(f"[KW-match] Raw tokens for input_id {input_id}: {raw_tokens}")

        matches = {}
        logger.debug(f"[KW-match] Processing input_id {input_id} with response_text: {response_text}")

        for theme, tag_info in tags.items():
            logger.debug(f"[KW-match] Processing theme: {theme} with keywords: {tag_info.get('keywords', [])}")
            logger.debug(f"[KW-match] Synonyms for theme {theme}: {tag_info.get('synonyms', {})}")

            matched_keywords = set()
            match_data = {"keywords": [], "matches": []}

            # Exact matches
            for keyword in tag_info.get("keywords", []):
                if keyword in tokens and keyword not in matched_keywords:
                    match_data["keywords"].append(keyword)
                    match_data["matches"].append({"type": "exact", "keyword": keyword})
                    matched_keywords.add(keyword)
                    logger.debug(f"[KW-match] Exact match found: {keyword} for theme: {theme}")

            # Synonym matches
            for key, synonyms in tag_info.get("synonyms", {}).items():
                for synonym in synonyms:
                    if synonym in tokens and key not in matched_keywords:
                        match_data["keywords"].append(key)
                        match_data["matches"].append({"type": "synonym", "keyword": key})
                        matched_keywords.add(key)
                        logger.debug(f"[KW-match] Synonym match found: {synonym} (key: {key}) for theme: {theme}")

            if not match_data["keywords"]:
                logger.debug(f"[KW-match] No matches found for theme: {theme} in input_id {input_id}")

            if match_data["keywords"]:
                matches[theme] = match_data
                logger.debug(f"[KW-match] Matches for theme {theme}: {match_data}")

        if matches:
            logger.debug(f"[KW-match] Updating database with matches for input_id {input_id}: {matches}")
            insert_keyword_match(logger, persona_id, input_id, matches)

    logger.info(f"[KW-match] Keyword matching completed for test_run_id: {test_run_id}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Keyword Matcher")
    parser.add_argument("test_run_id", type=int, help="test_run_id to process.")
    parser.add_argument("--reprocess", action="store_true", help="Reprocess all rows by resetting keyword_matches.")
    args = parser.parse_args()

    # Run keyword matcher with reprocess flag
    match_keywords(args.test_run_id, reprocess=args.reprocess)