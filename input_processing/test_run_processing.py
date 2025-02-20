import os
import sys
sys.path.append(os.path.dirname(__file__))
from normalizer import chunk_text
from ip_db_utils import get_inputs_for_test_run, update_chunks_in_db
from config import input_processing_logger as logger

def process_test_run(logger, test_run_id):
    """
    Process a test run: fetch inputs, chunk text, and update the database.
    """
    inputs = get_inputs_for_test_run(logger, test_run_id)

    for input_row in inputs:
        input_id, response_text = input_row
        if not response_text:
            logger.warning(f"[process_test_run] Skipping input_id {input_id}: empty response_text")
            continue

        chunks = chunk_text(logger, response_text, input_id=input_id)
        update_chunks_in_db(logger, input_id, chunks)

    logger.info(f"[process_test_run] Processed all inputs for test_run_id {test_run_id}")