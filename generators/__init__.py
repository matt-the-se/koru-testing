"""
Generators Package

This package contains scripts for generating personas with simulated responses to prompts, and user stories.
"""

# Import shared resources or modules
from config import DB_CONFIG, LOGGING_CONFIG, OPENAI_API_KEY

# Optionally, set up logging for the package
import logging
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Expose key functionalities directly
from ..old.generate_personas import generate_persona_foundation, process_personas_and_responses
from .generate_stories import generate_story