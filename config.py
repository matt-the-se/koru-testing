import os
from utils import setup_logger
import logging

# Base Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
GENERATORS_DIR = os.path.join(BASE_DIR, "generators")
INPUT_CLASSIFIER_DIR = os.path.join(BASE_DIR, "input-classifier")
INPUT_PROCESSING_DIR = os.path.join(BASE_DIR, "input-processing")
SHARED_DIR = os.path.join(BASE_DIR, "shared")
DEPENDENCIES_DIR = os.path.join(BASE_DIR, "dependencies")
STORY_QUALITY_DIR = os.path.join(BASE_DIR, "story-quality")

# Subdirectory and File Paths
SYNONYM_LIBRARY_PATH = os.path.join(SHARED_DIR, "synonym_library.json")
SENTIMENT_LIB_DIR = os.path.join(SHARED_DIR, "twitter-roBERTa-base-sentiment")
TEST_CASES_DIR = os.path.join(SHARED_DIR, "test-cases")
PERSONA_CREATION_DIR = os.path.join(SHARED_DIR, "persona-creation")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

# Database Configuration
DB_CONFIG = {
    "dbname": "testing_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5432,
}

# Thresholds
CHUNK_CONFIDENCE_THRESHOLD = 0.3
OVERALL_CONFIDENCE_THRESHOLD = 0.5
PROBABLE_THEME_BOOST = 1.1

# Ensure the logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Logging Configuration
GENERATE_PERSONAS_LOG = os.path.join(LOGS_DIR, "generate-personas.log")
GENERATE_STORIES_LOG = os.path.join(LOGS_DIR, "generate-stories.log")
INPUT_CLASSIFIER_LOG = os.path.join(LOGS_DIR, "input-classifier.log")
INPUT_PROCESSING_LOG = os.path.join(LOGS_DIR, "input-processing.log")
MAIN_LOG = os.path.join(LOGS_DIR, "koru-testing.log")

# Log Aggregation Setup
generate_personas_logger = setup_logger("generate_personas", GENERATE_PERSONAS_LOG)
generate_stories_logger = setup_logger("generate_stories", GENERATE_STORIES_LOG)
input_classifier_logger = setup_logger("input_classifier", INPUT_CLASSIFIER_LOG)
input_processing_logger = setup_logger("input_processing", INPUT_PROCESSING_LOG)
main_logger = setup_logger("main", MAIN_LOG)
