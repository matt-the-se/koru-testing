import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)
import argparse
from db_utils import reset_keyword_matches, save_clarity_scores
from config import input_processing_logger as logger
from pull_input_data import pull_clarity_score_inputs
from input_stats_report import generate_summary_report

def calculate_clarity_score(test_run_id, reprocess=False, generate_report=False):
    """
    Calculates the clarity score for a given test_run_id and optionally generates a report.
    Args:
        test_run_id (int): The test run ID to process.
        reprocess (bool): Whether to reprocess all rows by resetting keyword_matches.
        generate_report (bool): Whether to generate a summary report.
    """
    logger.info(f"[Clarity Score] Starting clarity score calculation for test_run_id: {test_run_id}")

    # Step 1: Handle keyword reprocessing if required
    if reprocess:
        logger.info(f"[Clarity Score] Reprocessing enabled. Resetting keyword_matches for test_run_id: {test_run_id}")
        reset_keyword_matches(test_run_id)

    # Step 2: Gather the required input data for persona_id clarity scoring
    logger.info(f"[Clarity Score] Gathering input data for test_run_id: {test_run_id}")
    input_data = pull_clarity_score_inputs(logger, test_run_id)
    
    if not input_data:
        logger.error(f"[Clarity Score] No input data found for test_run_id: {test_run_id}. Exiting calculation.")
        return

    persona_scores = {}
    for persona_id, persona_data in input_data.items():
        logger.info(f"[Clarity Score] Calculating clarity score for persona_id: {persona_id}")
        clarity_scores = calculate_clarity_score_logic(
            persona_data["aggregate_themes"],
            persona_data["complete_response_themes"],
            persona_data["probable_theme"],
            persona_data["chunk_scores"],
            persona_data["keyword_matches"],
            persona_data["foundation_complete"],
            persona_data["completeness_bucket"],
        )
        persona_scores[persona_id] = clarity_scores
        logger.info(f"[Clarity Score] Results for persona_id {persona_id}: {clarity_scores}")

    

    # Step 3: Optionally generate a summary report
    if generate_report:
        logger.info(f"[Clarity Score] Generating report for test_run_id: {test_run_id}")
        generate_summary_report(input_data)

    # Step 4: Calculate the clarity score using the provided logic
    logger.info(f"[Clarity Score] Calculating clarity score for test_run_id: {test_run_id}")

    # Extract necessary data from input_data
    aggregate_themes = input_data.get("aggregate_themes", {})
    complete_response_themes = input_data.get("complete_response_themes", {})
    probable_theme = input_data.get("probable_theme", (None, 0.0))
    chunk_scores = input_data.get("chunk_scores", [])
    keyword_matches = input_data.get("keyword_matches", {})
    foundation_complete = input_data.get("foundation_complete", True)
    completeness_bucket = input_data.get("completeness_bucket", 0.0)

    # Calculate clarity score
    clarity_scores = calculate_clarity_score_logic(
        aggregate_themes,
        complete_response_themes,
        probable_theme,
        chunk_scores,
        keyword_matches,
        foundation_complete,
        completeness_bucket,
    )
    # Step 5: Save the scores to the database
    for persona_id, persona_data in input_data.items():
        logger.info(f"[Clarity Score] Calculating clarity score for persona_id: {persona_id}")
    
        clarity_scores = calculate_clarity_score_logic(
            persona_data["aggregate_themes"],
            persona_data["complete_response_themes"],
            persona_data["probable_theme"],
            persona_data["chunk_scores"],
            persona_data["keyword_matches"],
            persona_data["foundation_complete"],
            persona_data["completeness_bucket"],
        )
        persona_scores[persona_id] = clarity_scores
        logger.info(f"[Clarity Score] Results for persona_id {persona_id}: {clarity_scores}")

        save_clarity_scores(logger, persona_id, clarity_scores)

    # Step 6: Log final clarity score results
    for persona_id, scores in persona_scores.items():
        logger.info(f"[Clarity Score] Persona {persona_id} Scores: {scores}")

    # Pretty print the scores in the terminal
    from tabulate import tabulate

    # Create a list of rows for the table
    table_rows = []
    for persona_id, scores in persona_scores.items():
        table_rows.append([
            persona_id,
            scores["total_clarity_score"],
            scores["core_vision_score"],
            scores["actualization_score"],
            scores["foundation_score"],
            scores["completeness_bucket"],
        ])

    # Define headers for the table
    headers = [
        "Persona ID",
        "Total Clarity Score",
        "Core Vision Score",
        "Actualization Score",
        "Foundation Score",
        "Completeness Bucket",
    ]

    # Print the table
    print("\nClarity Score Results:")
    print(tabulate(table_rows, headers=headers, tablefmt="grid", floatfmt=".2f"))

    return persona_scores


def calculate_clarity_score_logic(
    aggregate_themes,
    complete_response_themes,
    probable_theme,
    chunk_scores,
    keyword_matches,
    foundation_complete=True,
    completeness_bucket=0.0,
):
    """
    Perfect clarity scoring logic function.

    Args:
        aggregate_themes (dict): Aggregated chunk themes with their confidence scores.
        complete_response_themes (dict): Complete response themes with their confidence scores.
        probable_theme (tuple): Probable theme and its confidence (e.g., ("Spirituality and Purpose", 0.6)).
        chunk_scores (list): List of individual chunk themes and their confidence scores.
        keyword_matches (dict): Keyword match counts by theme.
        foundation_complete (bool): Whether the foundation is complete (default=True).
        completeness_bucket (float): Contribution from unmatched inputs (default=0.0).

    Returns:
        dict: Clarity score breakdown, including total clarity score and contributions per theme.
    """
    # Logic remains unchanged from your "perfect clarity scoring" logic

    # Weights
    foundation_weight = 0.1
    core_vision_weight = 0.4
    actualization_weight = 0.5

    # Initialize scores
    theme_scores = {
        "Spirituality and Purpose": 0.0,
        "Lifestyle and Environment": 0.0,
        "Leisure and Passions": 0.0,
        "Relationships and Community": 0.0,
        "Career and Contribution": 0.0,
        "Health and Well-being": 0.0,
        "Travel and Adventure": 0.0,
    }

    # Contribution tracker
    contributions = {
        "foundation": foundation_weight if foundation_complete else 0.0,
        "completeness_bucket": completeness_bucket,
        "themes": {},
    }

    # Core Vision Themes (40%)
    core_vision_themes = [
        "Spirituality and Purpose",
        "Lifestyle and Environment",
        "Leisure and Passions",
    ]

    # Actualization Themes (50%)
    actualization_themes = [
        "Relationships and Community",
        "Career and Contribution",
        "Health and Well-being",
        "Travel and Adventure",
    ]

    # Process each theme
    for theme in theme_scores:
        # Initialize theme contribution
        contributions["themes"][theme] = {
            "aggregate": 0.0,
            "complete_response": 0.0,
            "chunks": 0.0,
            "keywords": 0.0,
            "boost": 0.0,
        }

        # Aggregate Theme Contribution
        if theme in aggregate_themes:
            contributions["themes"][theme]["aggregate"] = aggregate_themes[theme]
            theme_scores[theme] += aggregate_themes[theme] * 0.4

        # Complete Response Theme Contribution
        if theme in complete_response_themes:
            contributions["themes"][theme]["complete_response"] = complete_response_themes[theme]
            theme_scores[theme] += complete_response_themes[theme] * 0.3

        # Chunk Contribution
        for chunk_theme, chunk_confidence in chunk_scores:
            if chunk_theme == theme:
                contributions["themes"][theme]["chunks"] += chunk_confidence
                theme_scores[theme] += chunk_confidence * 0.2

        # Keyword Match Contribution
        if theme in keyword_matches:
            keyword_score = keyword_matches[theme] * 0.1  # Adjust weight as needed
            contributions["themes"][theme]["keywords"] = keyword_score
            theme_scores[theme] += keyword_score

        # Boost for Overlap with Probable Theme
        if probable_theme[0] == theme:
            boost = probable_theme[1] * 0.1  # Adjust boost weight as needed
            contributions["themes"][theme]["boost"] = boost
            theme_scores[theme] += boost

    # Normalize Core Vision and Actualization scores
    core_vision_score = sum(theme_scores[t] for t in core_vision_themes)
    actualization_score = sum(theme_scores[t] for t in actualization_themes)

    normalized_core_vision = core_vision_score * core_vision_weight
    normalized_actualization = actualization_score * actualization_weight

    # Total Clarity Score
    total_clarity_score = (
        normalized_core_vision + normalized_actualization + contributions["foundation"] + contributions["completeness_bucket"]
    )

    # Final Output
    return {
        "total_clarity_score": total_clarity_score,
        "core_vision_score": normalized_core_vision,
        "actualization_score": normalized_actualization,
        "foundation_score": contributions["foundation"],
        "completeness_bucket": contributions["completeness_bucket"],
        "theme_contributions": contributions["themes"],
    }



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clarity Score Calculator")
    parser.add_argument("test_run_id", type=int, help="Test run ID to process.")
    parser.add_argument("--reprocess", action="store_true", help="Reprocess all rows by resetting keyword_matches.")
    parser.add_argument("--generate-report", action="store_true", help="Generate a summary report.")
    args = parser.parse_args()

    calculate_clarity_score(args.test_run_id, reprocess=args.reprocess, generate_report=args.generate_report)