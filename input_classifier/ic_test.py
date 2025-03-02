import os
import sys

# Add project root to path
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)

# Import the input classifier module
from input_classifier import process_test_run
from config import WEBAPP_DB_CONFIG, DB_CONFIG, input_classifier_logger as logger

def main():
    """
    Test script to run the input classifier on a specific test run.
    This allows reprocessing existing responses without reinputting all the information.
    """
    # Check if test_run_id was provided as command line argument
    if len(sys.argv) < 2:
        print("Usage: python ic_test.py <test_run_id>")
        sys.exit(1)
    
    try:
        test_run_id = int(sys.argv[1])
    except ValueError:
        print("Error: test_run_id must be an integer")
        sys.exit(1)
    
    print(f"Starting input classifier for test_run_id: {test_run_id}")
    
    # Process the test run
    try:
        process_test_run(test_run_id)
        print(f"Successfully processed test_run_id: {test_run_id}")
    except Exception as e:
        print(f"Error processing test_run_id {test_run_id}: {e}")
        logger.error(f"Error in ic_test.py: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 