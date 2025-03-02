from typing import Dict, Any
import sys
import os

# Handle imports differently based on how the file is being used
if __name__ == "__main__" or __package__ is None:
    # When run directly or from webapp
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from generate_stories.content_builder import ContentBuilder
    from generate_stories.persona_profile_builder import build_persona_profile
    from generate_stories.gs_db_utils import store_story, get_story_status, get_persona_id_from_test_run
    from generate_stories.gs_utils import validate_persona_data
else:
    # When imported as part of the package
    from .content_builder import ContentBuilder
    from .persona_profile_builder import build_persona_profile
    from .gs_db_utils import store_story, get_story_status, get_persona_id_from_test_run
    from .gs_utils import validate_persona_data

import openai
import argparse
from openai import OpenAI

def generate_story(test_run_id: int, persona_id: int = None) -> Dict[str, Any]:
    """Generate story using new content-focused approach
    
    Args:
        test_run_id: The test run ID
        persona_id: Optional persona ID. If not provided, it will be looked up from the test_run_id
    """
    
    # Look up persona_id if not provided
    if persona_id is None:
        persona_id = get_persona_id_from_test_run(test_run_id)
    
    # Get persona data using new profile builder
    persona_data = build_persona_profile(test_run_id, persona_id)
    
    # Build content guidance
    builder = ContentBuilder(persona_data)
    content = builder.build()
    
    # Generate story prompt
    prompt = builder.build_story_prompt(content)
    
    # Initialize OpenAI client
    client = OpenAI()
    
    # Generate story with OpenAI
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "system",
            "content": "You are a skilled storyteller who creates vivid, "
                      "intimate narratives in present tense, second person perspective."
        }, {
            "role": "user",
            "content": prompt
        }],
        temperature=0.85,  # Slightly higher for more creative variation
        max_tokens=1500
    )
    
    story = response.choices[0].message.content
    
    # Store story with prompt and persona_id
    store_story(test_run_id, story, prompt, persona_id)
    
    return {
        "status": "complete",
        "content": story,
        "prompt": prompt
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate a story for a specific test run and persona')
    parser.add_argument('test_run_id', type=int, help='Test run ID')
    parser.add_argument('--persona_id', type=int, help='Persona ID (optional, will be looked up if not provided)')
    
    args = parser.parse_args()
    
    # When called from webapp, only test_run_id is provided
    result = generate_story(args.test_run_id, args.persona_id)
    
    print("Story Generation Result:")
    print("Status:", result["status"])
    print("\nPrompt Used:")
    print(result["prompt"])
    print("\nGenerated Story:")
    print(result["content"]) 