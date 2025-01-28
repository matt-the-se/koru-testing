import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)
import json
from config import input_classifier_logger as logger

def load_synonym_library(file_path):
    """
    Load the synonym library from a JSON file.
    This file maps themes to their associated synonyms.
    """
    try:
        logger.info("[synonym_utils] loading synonym library.")
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        raise Exception(f"[synonym_utils] Error loading synonym library: {e}")

def generate_theme_embeddings(synonym_library, sbert_model, logger=None):
    """
    Generate embeddings for themes and their synonyms.
    """
    theme_embeddings = {}
    for theme, synonyms in synonym_library.items():
        try:
            theme_embeddings[theme] = {
                "main": sbert_model.encode(theme),
                "synonyms": [sbert_model.encode(synonym) for synonym in synonyms]
            }
        except Exception as e:
            if logger:
                logger.error(f"[synonym_utils] Error generating embeddings for theme '{theme}': {e}")
            continue
    return theme_embeddings