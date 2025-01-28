import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(base_path)
import argparse
import sys
import json
import time
from persona_test_loader import load_test_cases
from response_builder import process_personas_and_responses
from config import generate_personas_logger as logger, TEST_CASES_DIR, GENERATE_PERSONAS_LOG
from db_utils import (
    connect_db,
    create_test_run_id,
    fetch_prompts,
    summarize_results
)

import os

def track_progress_from_logs(log_file_path, total_responses):
    """
    Tracks progress of responses by monitoring log entries.
    Displays an ASCII progress bar in the console.
    """
    def update_progress_bar(current, total, bar_length=50):
        """
        Updates the ASCII progress bar.
        """
        progress = current / total
        blocks = int(bar_length * progress)
        bar = f"[{'#' * blocks}{'.' * (bar_length - blocks)}] {current}/{total} ({progress:.1%})"
        print(f"\r{bar}", end="", flush=True)

    # Ensure the log file exists before proceeding
    if not os.path.exists(log_file_path):
        print("Log file not found.")
        return

    # Track the number of responses from the log
    current_responses = 0

    with open(log_file_path, "r") as log_file:
        # Move to the end of the file to only track new entries
        log_file.seek(0, os.SEEK_END)

        while current_responses < total_responses:
            line = log_file.readline()
            if not line:
                # No new lines, wait and try again
                time.sleep(0.5)
                continue

            # Check if the log line indicates a response was stored in the database
            if "Response stored in database" in line:  # Adjust this to match the actual log message
                current_responses += 1
                update_progress_bar(current_responses, total_responses)

        # Finalize the progress bar
        print("\nAll responses have been generated!")
def calculate_total_responses(json_file_path, num_personas):
    """
    Calculate the total number of responses to be generated based on the JSON file and personas.
    """
    # Load JSON data
    with open(json_file_path, 'r') as file:
        data = json.load(file)

    # Extract detail levels and calculate multiplier
    detail_levels = data.get("detail_level", ["minimal", "moderate", "detailed"])
    if isinstance(detail_levels, str):
        detail_levels = [detail_levels]
    detail_multiplier = len(detail_levels)

    # Calculate the total number of prompts
    total_prompts = 0

    # Count freeform prompts
    total_prompts += len(data.get("freeform_prompts", []))

    # Count structured prompts and variations
    for structured_prompt in data.get("structured_prompts", []):
        total_prompts += 1  # Count the base prompt
        variations = structured_prompt.get("variations", [])
        total_prompts += len(variations)  # Count each variation

    # Calculate total responses
    total_responses = total_prompts * detail_multiplier * num_personas

    # Extract the AI model
    model_name = data.get("open_ai_model", "gpt-3.5-turbo")

    # Display confirmation
    print(f"\nConfirmation:")
    print(f"Personas: {num_personas}")
    print(f"Detail levels detected: {detail_multiplier}")
    print(f"Prompts detected in JSON: {total_prompts}")
    print(f"AI Model to be used: {model_name}")
    print(f"Total responses to be generated: {total_responses}")
    proceed = input("Proceed? (yes/no): ").strip().lower()

    if proceed != "yes":
        print("Exiting script as requested.")
        sys.exit(0)

def main(test_case_file, num_personas):
    logger.info("Starting persona_generator")
    try:
        # Step 1: Resolve the full path of the test case file in TEST_CASES_DIR
        test_case_path = os.path.join(TEST_CASES_DIR, test_case_file)
        if not os.path.exists(test_case_path):
            raise FileNotFoundError(f"Test case file not found: {test_case_path}")

        # Step 2: Display confirmation and calculate responses
        calculate_total_responses(test_case_path, num_personas)

        # Step 3: Connect to the database
        connection = connect_db(logger)
        cursor = connection.cursor()

        # Step 4: Load test case JSON
        logger.info(f"Loading test case file: {test_case_path}")
        test_cases = load_test_cases(logger, test_case_file, directory=TEST_CASES_DIR, validate_test_cases=True)

        # Extract the model name from the test case JSON
        model_name = test_cases.get("open_ai_model", "gpt-3.5-turbo")

        # Step 5: Create a new test run ID
        test_run_id = create_test_run_id(
            logger=logger,
            cursor=cursor,
            file_name=test_case_file,
            model_name=model_name,
            test_case_data=test_cases
        )
        logger.info(f"Created new test run ID: {test_run_id} from {test_case_file}.")

        # Step 6: Fetch prompts and variations from the database
        logger.info("Fetching prompts and variations from the database")
        prompts = fetch_prompts(logger, cursor, test_cases=test_cases)

        # Extract detail levels
        detail_levels = test_cases.get("detail_level", ["minimal", "moderate", "detailed"])
        detail_multiplier = len(detail_levels)

        # Calculate total responses
        total_prompts = len(test_cases.get("freeform_prompts", []))
        for structured_prompt in test_cases.get("structured_prompts", []):
            total_prompts += 1  # Base prompt
            total_prompts += len(structured_prompt.get("variations", []))  # Variations
        total_responses = total_prompts * detail_multiplier * num_personas

        # Step 7: Start tracking progress in a separate thread
        import threading
        progress_thread = threading.Thread(
            target=track_progress_from_logs,
            args=(GENERATE_PERSONAS_LOG, total_responses),
        )
        progress_thread.start()

        # Step 8: Generate responses using OpenAI
        logger.info("Generating responses for personas")
        process_personas_and_responses(
            logger=logger,
            prompts={
                "freeform_prompts": test_cases.get("freeform_prompts", []),
                "structured_prompts": test_cases.get("structured_prompts", []),
            },
            detail_levels=detail_levels,
            system_messages=test_cases["system_messages"],
            test_run_id=test_run_id,
            cursor=cursor,
            num_personas=num_personas,
            model_name=model_name
        )

        # Wait for the progress thread to finish
        progress_thread.join()

        # Step 9: Summarize and log results
        summary = summarize_results(logger, cursor, test_run_id)
        logger.info(f"Summary: {summary}")
        print(f"Summary: {summary}")

        # Commit changes and close connections
        connection.commit()
        cursor.close()
        connection.close()

    except Exception as e:
        logger.error(f"Error in persona_generator main: {e}")
        raise

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Run persona generator with a specific test case file.")
    parser.add_argument(
        "-t",
        "--testcase",
        type=str,
        required=True,
        help="Name of the test case JSON file located in TEST_CASES_DIR."
    )
    parser.add_argument(
        "-p",
        "--personas",
        type=int,
        default=1,
        help="Number of personas to generate (default: 1)."
    )
    args = parser.parse_args()

    # Call the main function with the provided arguments
    main(args.testcase, args.personas)
