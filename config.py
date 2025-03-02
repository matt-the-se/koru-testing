import os
from utils import setup_logger
import logging
from typing import Dict
from dotenv import load_dotenv
from logging.config import dictConfig
import json
import sys

load_dotenv()

# Base Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
GENERATORS_DIR = os.path.join(BASE_DIR, "generators")
INPUT_CLASSIFIER_DIR = os.path.join(BASE_DIR, "input_classifier")
INPUT_PROCESSING_DIR = os.path.join(BASE_DIR, "input_processing")
SHARED_DIR = os.path.join(BASE_DIR, "shared")
DEPENDENCIES_DIR = os.path.join(BASE_DIR, "dependencies")
STORY_QUALITY_DIR = os.path.join(BASE_DIR, "story_quality")
GENERATE_STORIES_DIR = os.path.join(BASE_DIR, "generate_stories")

# Add to Python path at config load time
sys.path.extend([
    BASE_DIR,
    INPUT_PROCESSING_DIR,
    INPUT_CLASSIFIER_DIR
])

# Subdirectory and File Paths
SYNONYM_LIBRARY_PATH = os.path.join(SHARED_DIR, "synonym_library.json")
SENTIMENT_LIB_DIR = os.path.join(SHARED_DIR, "twitter-roBERTa-base-sentiment")
TEST_CASES_DIR = os.path.join(SHARED_DIR, "test_cases")
PERSONA_CREATION_DIR = os.path.join(SHARED_DIR, "persona_creation")

# API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# SQLAlchemy URL for webapp
def get_db_url(config: Dict) -> str:
    return f"postgresql://{config['user']}:{config['password']}@{config['host']}/{config['dbname']}"

# Database Configuration
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5432,
}

WEBAPP_DB_CONFIG = {
    **DB_CONFIG,  # Inherit base config
    "dbname": "koru_data"  # Your production DB
}

# SQLAlchemy URLs
SQLALCHEMY_DATABASE_URL = get_db_url(WEBAPP_DB_CONFIG)

# Thresholds
CHUNK_CONFIDENCE_THRESHOLD = 0.3
OVERALL_CONFIDENCE_THRESHOLD = 0.5
PROBABLE_THEME_BOOST = 1.1

# Input Classifier Confidence Thresholds
CONFIDENCE_THRESHOLDS = {
    'min_confidence': CHUNK_CONFIDENCE_THRESHOLD,  # Use existing threshold
    'multi_theme': OVERALL_CONFIDENCE_THRESHOLD,   # Use existing threshold
    'probable_theme_boost': PROBABLE_THEME_BOOST   # Use existing boost value
}

# Ensure the logs directory exists
os.makedirs(LOGS_DIR, exist_ok=True)

# Original Logging Configuration
GENERATE_PERSONAS_LOG = os.path.join(LOGS_DIR, "generate_personas.log")
GENERATE_STORIES_LOG = os.path.join(LOGS_DIR, "generate_stories.log")
INPUT_CLASSIFIER_LOG = os.path.join(LOGS_DIR, "input_classifier.log")
INPUT_PROCESSING_LOG = os.path.join(LOGS_DIR, "input_processing.log")
MAIN_LOG = os.path.join(LOGS_DIR, "koru_testing.log")

# Original Log Aggregation Setup
generate_personas_logger = setup_logger("generate_personas", GENERATE_PERSONAS_LOG)
generate_stories_logger = setup_logger("generate_stories", GENERATE_STORIES_LOG)
input_classifier_logger = setup_logger("input_classifier", INPUT_CLASSIFIER_LOG)
input_processing_logger = setup_logger("input_processing", INPUT_PROCESSING_LOG)
main_logger = setup_logger("main", MAIN_LOG)

# Flask configs
FLASK_CONFIG = {
    "SECRET_KEY": os.getenv('FLASK_SECRET_KEY', 'dev'),
    "DEBUG": os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't'),
    "SESSION_COOKIE_NAME": "koru_session",
    "SESSION_COOKIE_SECURE": True,
    "TEMPLATES_AUTO_RELOAD": True,
    "SEND_FILE_MAX_AGE_DEFAULT": 0
}

# Flask Logging Configuration
WEBAPP_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,  # Important to keep existing loggers
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stdout',
        },
        'file': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'webapp.log'),
            'mode': 'a',
        },
    },
    'loggers': {
        'webapp': {
            'handlers': ['default', 'file'],
            'level': 'INFO',
            'propagate': False
        },
    }
}

# Initialize webapp logging
dictConfig(WEBAPP_LOGGING_CONFIG)
webapp_logger = logging.getLogger('webapp')
