import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)
import spacy
from config import input_processing_logger as logger


# Load SpaCy model
nlp = spacy.load("en_core_web_sm")

def chunk_text(logger, text, input_id=None, max_chunk_size=200, min_sentence_length=50, overlap_size=100):
    """
    Split text into semantically coherent overlapping chunks with dynamic handling for short and long sentences.
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
                logger.debug(f"[normalizer] Chunk created for input_id {input_id}: {chunks[-1]}")
                chunk_id += 1

        # Case 4: Finalize the current chunk and start a new one
        else:
            chunks.append({"chunk_id": chunk_id, "chunk_text": " ".join(current_chunk)})
            logger.debug(f"[normalizer] Chunk created for input_id {input_id}: {chunks[-1]}")
            overlap_text = " ".join(current_chunk)[-overlap_size:] if overlap_size > 0 else ""
            current_chunk = [overlap_text, sentence_text] if overlap_text else [sentence_text]
            current_length = len(" ".join(current_chunk))
            chunk_id += 1

    # Add the final chunk
    if current_chunk:
        chunks.append({"chunk_id": chunk_id, "chunk_text": " ".join(current_chunk)})
        logger.debug(f"[normalizer] Chunk created for input_id {input_id}: {chunks[-1]}")

    return chunks