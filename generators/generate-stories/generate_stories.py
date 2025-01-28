import argparse
from config import generate_stories_logger as logger
from db_utils import fetch_persona_data, fetch_all_personas_in_test_run
from theme_prioritizer import prioritize_themes

def main():
    """
    Main script to generate stories for personas. Fetches data, prioritizes themes, and prepares for story generation.
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate stories for personas.")
    parser.add_argument("-t", "--test_run_id", type=int, required=True, help="The test run ID.")
    parser.add_argument("-p", "--persona_id", type=int, help="The ID of a specific persona (optional).")
    args = parser.parse_args()

    # If persona_id is provided, process only that persona
    if args.persona_id:
        logger.info(f"Fetching data for persona_id={args.persona_id}, test_run_id={args.test_run_id}")
        persona_data = fetch_persona_data(args.persona_id, args.test_run_id)

        if persona_data:
            process_persona(persona_data)
        else:
            logger.warning(f"No data found for persona_id={args.persona_id} and test_run_id={args.test_run_id}")
            print(f"No data found for persona_id={args.persona_id} and test_run_id={args.test_run_id}")
    else:
        # If no persona_id is provided, process all personas for the test run
        logger.info(f"Fetching data for all personas in test_run_id={args.test_run_id}")
        all_personas = fetch_all_personas_in_test_run(args.test_run_id)

        if all_personas:
            for persona_data in all_personas:
                process_persona(persona_data)
        else:
            logger.warning(f"No data found for test_run_id={args.test_run_id}")
            print(f"No data found for test_run_id={args.test_run_id}")

def process_persona(persona_data):
    """
    Process a single persona, prioritizing themes and preparing for story generation.

    Args:
        persona_data (dict): Data for a single persona.
    """
    thresholds = {
        "CHUNK_CONFIDENCE_THRESHOLD": 0.4,
        "OVERALL_CONFIDENCE_THRESHOLD": 0.6,
        "PROBABLE_THEME_BOOST": 1.1
    }

    # Prioritize themes
    logger.info(f"Prioritizing themes for persona_id={persona_data['inputs'][0]['persona_id']}")
    prioritized_themes = prioritize_themes(persona_data, thresholds)

    # Output results
    print(f"Persona ID: {persona_data['inputs'][0]['persona_id']}")
    print("Primary Theme:", prioritized_themes["primary_theme"])
    print("Secondary Themes:", prioritized_themes["secondary_themes"])
    print("Adjusted Weights:", prioritized_themes["adjusted_weights"])

    logger.info(f"Theme prioritization completed for persona_id={persona_data['inputs'][0]['persona_id']}")

if __name__ == "__main__":
    main()