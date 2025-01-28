import sys
import logging
from config import BASE_DIR, LOGS_DIR, CLASSIFIER_DIR, GENERATORS_DIR

# Add project directories to sys.path
sys.path.append(BASE_DIR)
sys.path.append(CLASSIFIER_DIR)
sys.path.append(GENERATORS_DIR)

# Example imports from modular structure
from classifier.input_classifier import classify_chunk
from generators.persona_generator import generate_persona

# Initialize logging
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Koru-Testing Project")

    # Test classification script
    sample_input = "This is a test chunk."
    classified_output = classify_chunk(sample_input)
    logger.info(f"Classification Result: {classified_output}")

    # Test persona generation
    persona = generate_persona()
    logger.info(f"Generated Persona: {persona}")

if __name__ == "__main__":
    main()