from config import generate_stories_logger as logger

def prioritize_themes(persona_data, thresholds):
    """
    Prioritize themes for a persona based on extracted themes, frequencies, and response stats.

    Args:
        persona_data (dict): The data for the persona including foundations, inputs, and test_run_id.
        thresholds (dict): Threshold configuration for confidence and emphasis.

    Returns:
        dict: A dictionary containing primary theme(s), secondary themes, and adjusted weights.
    """
    primary_theme = None
    secondary_themes = []
    adjusted_weights = {}

    # Thresholds
    chunk_conf_threshold = thresholds.get("CHUNK_CONFIDENCE_THRESHOLD", 0.3)
    probable_theme_boost = thresholds.get("PROBABLE_THEME_BOOST", 1.5)
    fallback_confidence = 0.3  # Default confidence for fallback themes

    logger.info(f"[theme_pri] Processing persona data for test_run_id: {persona_data['test_run_id']}")

    for input_data in persona_data["inputs"]:
        probable_theme = input_data.get("prompt_theme")
        extracted_themes = input_data.get("extracted_themes", {})
        extracted_theme_count = input_data.get("extracted_theme_count", {})
        if not extracted_theme_count:
            logger.warning(f"[theme_pri] Missing extracted_theme_count for input ID {input_data['input_id']}. Skipping.")
            continue

        response_stats = input_data.get("response_stats")  # Safely access response_stats

        logger.info(f"[theme_pri] Input ID: {input_data['input_id']} | Probable Theme: {probable_theme}")
        logger.info(f"[theme_pri] Extracted Themes: {extracted_themes}")

        # Skip inputs with no extracted themes
        if not extracted_themes or not extracted_themes.get("chunks"):
            logger.warning(f"[theme_pri] No valid themes for input ID {input_data['input_id']}. Skipping.")
            continue

        # Aggregate themes from chunks
        aggregated = extracted_themes.get("aggregated", {})
        highest_freq_theme = max(aggregated, key=aggregated.get, default=None)
        highest_freq_count = aggregated.get(highest_freq_theme, 0)

        logger.info(f"[theme_pri] Highest Frequency Theme: {highest_freq_theme} ({highest_freq_count})")

        # Response-level confidence integration
        response_confidence = extracted_themes.get("response_text", {}).get("confidence", {})
        response_theme = max(response_confidence, key=response_confidence.get, default=None)
        response_conf_value = response_confidence.get(response_theme, 0)

        # Determine primary theme
        if response_theme and response_conf_value > aggregated.get(highest_freq_theme, 0):
            primary_theme = response_theme
            logger.info(f"[theme_pri] Primary theme set to Response Theme: {primary_theme} (Confidence: {response_conf_value})")
        elif probable_theme and probable_theme == highest_freq_theme:
            primary_theme = probable_theme
            logger.info(f"[theme_pri] Primary theme set to Probable Theme: {primary_theme}")
        elif probable_theme:
            primary_theme = probable_theme
            logger.info(f"[theme_pri] Fallback to Probable Theme: {primary_theme}")
        else:
            # Ensure consistent primary theme format (e.g., avoid dictionaries or detailed themes)
            if isinstance(response_theme, dict):
                response_theme = next(iter(response_theme.keys()))  # Extract parent theme only
            if isinstance(highest_freq_theme, dict):
                highest_freq_theme = next(iter(highest_freq_theme.keys()))  # Extract parent theme only
            if isinstance(probable_theme, dict):
                probable_theme = next(iter(probable_theme.keys()))  # Extract parent theme only

            # Finalize primary theme based on conditions
            primary_theme = response_theme or highest_freq_theme
            logger.info(f"[theme_pri] Primary theme set to fallback: {primary_theme}")

        # Adjust weights using response stats
        if response_stats:
            input_length_scores = response_stats.get("aggregate_input_length_scores", {})
            for theme, score in input_length_scores.items():
                weight = extracted_theme_count.get(theme, 0) * score if extracted_theme_count else 0
                if theme == probable_theme:
                    weight *= probable_theme_boost
                adjusted_weights[theme] = adjusted_weights.get(theme, 0) + weight
                logger.info(f"[theme_pri] Theme: {theme} | Weight Updated: {adjusted_weights[theme]}")
                
        # Safeguard extracted_theme_count iteration
        if extracted_theme_count:
            for theme, count in extracted_theme_count.items():
                logger.info(f"[theme_pri] Extracted Theme Count | Theme: {theme}, Count: {count}")

        else:
            # Fallback mechanism if response stats are missing
            for theme, count in extracted_theme_count.items():

            # Ensure extracted_theme_count is a dictionary
                extracted_theme_count = extracted_theme_count or {}
                for theme, count in extracted_theme_count.items():
                    logger.info(f"[theme_pri] Extracted Theme Count | Theme: {theme}, Count: {count}")
                    adjusted_weights[theme] = adjusted_weights.get(theme, 0) + count
                if theme == probable_theme:
                    adjusted_weights[theme] *= probable_theme_boost

        # Add secondary themes
        for chunk in extracted_themes.get("chunks", []):
            for theme, conf in chunk.get("confidence", {}).items():
                if conf >= thresholds.get("CHUNK_CONFIDENCE_THRESHOLD", 0.25) and theme not in secondary_themes:
                    secondary_themes.append(theme)

        # Fallback: Include response themes if chunks are insufficient
        if not secondary_themes and "response_themes" in extracted_themes.get("response_text", {}):
            secondary_themes = extracted_themes["response_text"]["response_themes"]

        # Add response-level theme to secondary themes if not present
        if response_theme and response_theme != primary_theme and response_theme not in secondary_themes:
            secondary_themes.append(response_theme)
            logger.info(f"[theme_pri] Added Response Theme to Secondary Themes: {response_theme}")

    # Deduplicate secondary themes and sort by adjusted weight
    secondary_themes = sorted(
        set(
            next(iter(theme.keys())) if isinstance(theme, dict) else theme  # Strip detailed themes
            for theme in secondary_themes 
            if theme != primary_theme
        ), 
        key=lambda t: adjusted_weights.get(t, 0), 
        reverse=True
    )

    # Log final results
    logger.info(f"[theme_pri] Final Primary Theme: {primary_theme}")
    logger.info(f"[theme_pri] Final Secondary Themes: {secondary_themes}")
    logger.info(f"[theme_pri] Adjusted Weights: {adjusted_weights}")

    return {
        "primary_theme": primary_theme,
        "secondary_themes": secondary_themes,
        "adjusted_weights": adjusted_weights
    }