"""
Shared Resources and Libraries

This package contains shared data files, libraries, and utilities used throughout the project.
"""

import os

# Define paths to shared resources for easy access
SHARED_DIR = os.path.dirname(__file__)
PERSONA_CREATION_DIR = os.path.join(SHARED_DIR, "persona-creation")
TEST_CASES_DIR = os.path.join(SHARED_DIR, "test-cases")
SENTIMENT_LIB_DIR = os.path.join(SHARED_DIR, "twitter-roBERTa-base-sentiment")

# Define paths to individual shared files
SYNONYM_LIBRARY_PATH = os.path.join(SHARED_DIR, "synonym_library.json")
ABBREV_SLANG_LIBRARY_PATH = os.path.join(SHARED_DIR, "abbrev-slang-library.csv")

# Define paths for persona creation files
ANIMALS_JSON = os.path.join(PERSONA_CREATION_DIR, "animals.json")
LOCATIONS_GENERIC_JSON = os.path.join(PERSONA_CREATION_DIR, "locations-generic.json")
LOCATIONS_SPECIFIC_JSON = os.path.join(PERSONA_CREATION_DIR, "locations-specific.json")
NAMES_FIRST_JSON = os.path.join(PERSONA_CREATION_DIR, "names-first.json")
NAMES_LAST_JSON = os.path.join(PERSONA_CREATION_DIR, "names-last.json")

# Define paths for test case files
GENERATOR_TESTING_COMPLETE_JSON = os.path.join(TEST_CASES_DIR, "generator-testing-complete.json")
GENERATOR_TESTING_SMALL_JSON = os.path.join(TEST_CASES_DIR, "generator-testing-small.json")