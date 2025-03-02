import os
import sys
import argparse

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

# Import the specific modules directly
from generate_stories.generate_stories import generate_story
from generate_stories.gs_db_utils import set_db_config
from config import WEBAPP_DB_CONFIG

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test story generation')
    parser.add_argument('--test_run_id', type=int, default=132, help='Test run ID')
    parser.add_argument('--persona_id', type=int, default=None, help='Persona ID (optional)')
    parser.add_argument('--lookup', action='store_true', help='Test persona_id lookup')
    
    args = parser.parse_args()
    
    # Simulate webapp setting the DB config
    set_db_config(WEBAPP_DB_CONFIG)
    
    test_run_id = args.test_run_id
    persona_id = None if args.lookup else args.persona_id
    
    print(f"Testing with test_run_id={test_run_id}" + 
          (f", persona_id={persona_id}" if persona_id else ", persona_id=None (will be looked up)"))

    result = generate_story(test_run_id, persona_id)

    print("Story Generation Result:")
    print("Status:", result["status"])
    print("\nPrompt Used:")
    print(result["prompt"])
    print("\nGenerated Story:")
    print(result["content"])

if __name__ == "__main__":
    main()