import argparse
import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)
from test_run_processing import process_test_run
from config import input_processing_logger as logger


def main():
    """
    Main entry point: Parse arguments and process test runs.
    """
    parser = argparse.ArgumentParser(description="Chunk response texts for a specific test run ID.")
    parser.add_argument("test_run_id", type=int, help="The ID of the test run to process.")
    args = parser.parse_args()

    try:
        process_test_run(logger, args.test_run_id)
    except Exception as e:
        logger.error(f"[input_chunker] Error processing test_run_id {args.test_run_id}: {e}")

if __name__ == "__main__":
    main()