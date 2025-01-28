import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from config import input_classifier_logger as logger
def classify_chunk(chunk_text, probable_theme, sbert_model, theme_embeddings, logger):
    """
    Classify a text chunk by calculating similarities to predefined themes.
    Includes a probable theme boost for higher confidence matching.
    """
    try:
        # Generate embedding for the text chunk
        chunk_embedding = sbert_model.encode(chunk_text)

        # Debug log for theme embeddings
        logger.debug(f"[post_proc] theme_embeddings keys: {list(theme_embeddings.keys())}")

        # Validate each theme and calculate similarities
        similarities = {}
        for theme, data in theme_embeddings.items():
            if not isinstance(theme, str):
                logger.error(f"[post_proc] Invalid theme key (not a string): {theme}")
                continue
            if not isinstance(data, dict) or "main" not in data or "synonyms" not in data:
                logger.error(f"[post_proc] Invalid data structure for theme '{theme}': {data}")
                continue

            # Calculate main theme similarity
            main_similarity = cosine_similarity([chunk_embedding], [data["main"]])[0][0]
            
            # Calculate max synonym similarity
            synonym_similarities = [
                cosine_similarity([chunk_embedding], [syn_embedding])[0][0]
                for syn_embedding in data["synonyms"]
                if isinstance(syn_embedding, (list, tuple))  # Ensure valid type
            ]
            max_synonym_similarity = max(synonym_similarities, default=0)
            
            # Store the maximum similarity
            similarities[theme] = max(main_similarity, max_synonym_similarity)

        # Boost similarity for the probable theme
        if probable_theme in similarities:
            similarities[probable_theme] *= 1.05

        # Sort themes by similarity scores
        sorted_similarities = sorted(similarities.items(), key=lambda x: x[1], reverse=True)

        # Log confidence scores for each theme
        logger.info(f"Confidence scores for chunk '{chunk_text[:50]}...': {sorted_similarities}")

        # Filter themes based on thresholds
        matching_themes = [(theme, score) for theme, score in sorted_similarities if score >= 0.3]

        # Build matching_scores as a dictionary
        matching_scores = {theme: score for theme, score in matching_themes}

        # Log when no themes match
        if not matching_themes:
            if probable_theme == "Not Used":
                logger.warning(f"[post_proc] No themes matched for freeform chunk: {chunk_text[:50]}...")
                return [], matching_scores  # No fallback, return empty list for chunk_themes
            else:
                logger.warning(f"[post_proc] Returning probable_theme '{probable_theme}' as fallback for chunk: {chunk_text[:50]}...")
                return [probable_theme], matching_scores

        single_theme = (
            matching_themes[0][0]
            if len(matching_themes) == 1 or
            matching_themes[0][1] >= 1.2 * matching_themes[1][1]
            else None
        )
        multi_themes = [theme for theme, score in matching_themes if score >= 0.5]
        logger.debug(f"[post_proc!] Returning from classify_chunk: themes={multi_themes if single_theme is None else [single_theme]}, scores={matching_themes}")
        # Ensure at least one theme is returned
        if single_theme is None and not multi_themes:
            logger.warning(f"[post_proc] Returning probable_theme '{probable_theme}' as fallback for chunk: {chunk_text[:50]}...")
            return [probable_theme], matching_scores  # Use probable_theme as fallback

        return multi_themes if single_theme is None else [single_theme], matching_scores

    except Exception as e:
        raise Exception(f"Error classifying chunk: {e}")

def aggregate_themes(classified_chunks, synonym_library):
    """
    Aggregate classified themes across all chunks.
    """
    aggregated_themes = {"chunks": classified_chunks, "aggregated": {theme: 0 for theme in synonym_library.keys()}}
    
    for chunk in classified_chunks:
        if not isinstance(chunk["chunk_themes"], list):
            logger.warning(f"[post_proc] Skipping invalid chunk with chunk_themes: {chunk}")
            continue  # Skip invalid chunks
        
        for theme in chunk["chunk_themes"]:
            aggregated_themes["aggregated"][theme] += 1

    return aggregated_themes

def calculate_input_length_score(response_text_length, theme_count):
    """
    Calculate the detail score for a theme based on response text length and theme frequency.
    """
    # Normalize the score by dividing theme count by response_text length
    score = theme_count / response_text_length if response_text_length > 0 else 0
    # Scale to a range [0, 1]
    return min(max(score, 0), 1)

def calculate_response_stats(response_text, extracted_theme_count, probable_theme):
    """
    Calculate response stats, including word count and input length scores.
    """
    # Word count for response_text
    word_count = len(response_text.split())
    
    # Aggregate input length scores
    aggregate_input_length_scores = {}
    if extracted_theme_count:
        for theme, count in extracted_theme_count.items():
            aggregate_input_length_scores[theme] = calculate_input_length_score(word_count, count)
    else:
        # Fallback to probable theme
        aggregate_input_length_scores[probable_theme] = calculate_input_length_score(word_count, 1)

    return {
        "word_count": word_count,
        "aggregate_input_length_scores": aggregate_input_length_scores,
        "probable_length_score": aggregate_input_length_scores.get(probable_theme, 0)
    }

def calculate_theme_frequencies(extracted_themes, probable_theme):
    """
    Calculate the frequency of each theme from chunk data. If no themes are found,
    fallback to the probable theme with its confidence score from chunk confidence.
    """
    theme_count = {}

    # Validate and retrieve chunks
    chunks = extracted_themes.get("chunks", [])
    if not chunks:
        logger.error("[post_proc] No chunks to process for theme frequencies.")
        return {}

    # Process each chunk
    for chunk in chunks:
        # Validate chunk structure
        if not isinstance(chunk, dict):
            logger.warning(f"[post_proc] Invalid chunk type: {type(chunk)}. Skipping chunk: {chunk}")
            continue

        # Validate or fix 'chunk_themes'
        if "chunk_themes" not in chunk or not isinstance(chunk["chunk_themes"], list):
            logger.warning(f"[post_proc] Fixing missing or invalid 'chunk_themes': {chunk}")
            chunk["chunk_themes"] = []  # Default to empty list

        # Count themes
        for chunk in extracted_themes.get("chunks", []):
            for theme in chunk.get("chunk_themes", []):
                theme_count[theme] = theme_count.get(theme, 0) + 1

    logger.info(f"[post_proc] Final theme counts: {theme_count}")

    # Fallback to probable theme if no themes are found
    if not theme_count:
        logger.debug(f"[post_proc] No themes found. Falling back to probable_theme: {probable_theme}.")
        probable_confidence = max(
            (
                chunk.get("confidence", {}).get(probable_theme, 0)
                for chunk in extracted_themes.get("chunks", [])
            ),
            default=0,
        )
        theme_count[probable_theme] = probable_confidence or 1  # Default confidence of 1 if no data is available

    return theme_count