import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from config import WEBAPP_DB_CONFIG  # Get the webapp config
from generate_stories.gs_db_utils_build import set_db_config  # Import the config setter
from generate_stories.generate_stories_build import generate_story_build  # Updated import

def main():
    # Simulate webapp setting the DB config
    set_db_config(WEBAPP_DB_CONFIG)
    
    # Test with known test_run_id and persona_id
    test_run_id = 131
    persona_id = 128

    result = generate_story_build(test_run_id, persona_id)  # Updated call

    print("Story Generation Result:")
    print("Status:", result["status"])
    print("\nPrompt Used:")
    print(result["prompt"])
    print("\nGenerated Story:")
    print(result["content"])

if __name__ == "__main__":
    main() 