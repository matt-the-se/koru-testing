import os
import argparse
import psycopg2
import spacy
import json
from config import DB_CONFIG, LOGS_DIR, setup_logger

# Configure logging from config.py
INPUT_CLASSIFIER_LOG = os.path.join(LOGS_DIR, "input_chunker.log")
logger = setup_logger("input_chunker", INPUT_CLASSIFIER_LOG)

# Load SpaCy model
nlp = spacy.load("en_core_web_sm")

def chunk_text(text, input_id=None, max_chunk_size=200, min_sentence_length=50, overlap_size=100):
    """
    Split text into semantically coherent overlapping chunks with dynamic handling for short and long sentences.

    Args:
        text (str): The input text to be chunked.
        input_id (int): The ID of the input being processed (optional, for logging).
        max_chunk_size (int): The maximum character length for a chunk.
        min_sentence_length (int): The minimum length for a sentence to remain independent.
        overlap_size (int): The number of overlapping characters between consecutive chunks.

    Returns:
        list: A list of chunk dictionaries containing chunk ID and text.
    """
    doc = nlp(text)
    chunks = []
    current_chunk = []
    chunk_id = 1
    current_length = 0

    for sentence in doc.sents:
        sentence_text = sentence.text.strip()
        sentence_length = len(sentence_text)

        # Case 1: Combine short sentences with the current chunk
        if sentence_length < min_sentence_length:
            if current_length + sentence_length <= max_chunk_size:
                current_chunk.append(sentence_text)
                current_length += sentence_length
            else:
                chunks.append({"chunk_id": chunk_id, "chunk_text": " ".join(current_chunk)})
                logger.debug(f"Chunk created for input_id {input_id}: {chunks[-1]}")
                current_chunk = [sentence_text]
                current_length = sentence_length
                chunk_id += 1

        # Case 2: Regular sentence fitting into the chunk
        elif current_length + sentence_length <= max_chunk_size:
            current_chunk.append(sentence_text)
            current_length += sentence_length

        # Case 3: Long sentence exceeding max_chunk_size
        elif sentence_length > max_chunk_size:
            words = sentence_text.split()
            for i in range(0, len(words), max_chunk_size - overlap_size):
                chunk_text = " ".join(words[i:i + max_chunk_size])
                chunks.append({"chunk_id": chunk_id, "chunk_text": chunk_text})
                logger.debug(f"Chunk created for input_id {input_id}: {chunks[-1]}")
                chunk_id += 1

        # Case 4: Finalize the current chunk and start a new one
        else:
            chunks.append({"chunk_id": chunk_id, "chunk_text": " ".join(current_chunk)})
            logger.debug(f"Chunk created for input_id {input_id}: {chunks[-1]}")
            overlap_text = " ".join(current_chunk)[-overlap_size:] if overlap_size > 0 else ""
            current_chunk = [overlap_text, sentence_text] if overlap_text else [sentence_text]
            current_length = len(" ".join(current_chunk))
            chunk_id += 1

    # Add the final chunk
    if current_chunk:
        chunks.append({"chunk_id": chunk_id, "chunk_text": " ".join(current_chunk)})
        logger.debug(f"Chunk created for input_id {input_id}: {chunks[-1]}")

    return chunks

def update_chunks_in_db(input_id, chunks, conn):
    """
    Update the persona_inputs table with chunked data.

    Args:
        input_id (int): The ID of the input being updated.
        chunks (list): List of chunk dictionaries to be stored.
        conn (psycopg2 connection): Database connection.
    """
    cursor = conn.cursor()
    query = """
    UPDATE persona_inputs
    SET extracted_themes = %s
    WHERE input_id = %s;
    """
    try:
        cursor.execute(query, (json.dumps({"chunks": chunks}), input_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating persona_inputs for input_id {input_id}: {e}")
        conn.rollback()
    finally:
        cursor.close()

def process_test_run(test_run_id):
    """
    Fetch inputs for a test run, chunk the response_text, and update the database.

    Args:
        test_run_id (int): The ID of the test run to process.
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    query = """
    SELECT input_id, response_text
    FROM persona_inputs
    WHERE test_run_id = %s;
    """
    try:
        cursor.execute(query, (test_run_id,))
        inputs = cursor.fetchall()
        logger.info(f"Fetched {len(inputs)} inputs for test_run_id {test_run_id}")

        for input_row in inputs:
            input_id, response_text = input_row
            if not response_text:
                logger.warning(f"Skipping input_id {input_id}: empty response_text")
                continue

            chunks = chunk_text(response_text, input_id=input_id)
            update_chunks_in_db(input_id, chunks, conn)

        logger.info(f"Processed all inputs for test_run_id {test_run_id}")
    except Exception as e:
        logger.error(f"Error processing test_run_id {test_run_id}: {e}")
    finally:
        cursor.close()
        conn.close()

def main():
    """
    Main entry point: Parse arguments and process test runs.
    """
    parser = argparse.ArgumentParser(description="Chunk response texts for a specific test run ID.")
    parser.add_argument("test_run_id", type=int, help="The ID of the test run to process.")
    args = parser.parse_args()
    process_test_run(args.test_run_id)

if __name__ == "__main__":
    main()