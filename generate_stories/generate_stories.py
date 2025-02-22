import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)
import random
import json
import psycopg2
import argparse
from openai import OpenAI
from config import OPENAI_API_KEY, generate_stories_logger as logger, DB_CONFIG
from persona_profile_builder import build_persona_profile
import uuid
# Near where you create the OpenAI client
logger.info(f"API Key being used (first 8 chars): {OPENAI_API_KEY[:8] if OPENAI_API_KEY else 'None'}")
client = OpenAI(api_key=OPENAI_API_KEY)

# Utility Function: Shuffle Prompt Components
def shuffle_prompt_components(components):
    """
    Shuffle the logical chunks of the prompt to introduce natural variability.

    Args:
        components (list): List of prompt components (strings).

    Returns:
        str: Reorganized prompt as a single string.
    """
    random.shuffle(components)
    return "\n".join(components)

def store_story_prompts(test_run_id, persona_id, prompt, story_themes):
    """
    Store the generated story prompt in the database and return the generated story_id.

    Args:
        test_run_id (int): The test run ID.
        persona_id (int): The persona ID.
        prompt (str): The generated story prompt.
        story_themes (dict): The themes used in the story.

    Returns:
        tuple: (story_id, test_run_id) to ensure consistency.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Ensure test_run_id is set
        if test_run_id is None:
            cur.execute("SELECT test_run_id FROM personas WHERE persona_id = %s;", (persona_id,))
            result = cur.fetchone()
            if result:
                test_run_id = result[0]
            else:
                logger.error(f"Failed to fetch test_run_id for persona_id={persona_id}")
                return None, None

        logger.info(f"Storing story prompt for persona_id={persona_id}, test_run_id={test_run_id}")
        logger.info(f"Prompt: {prompt}")

        cur.execute("""
            INSERT INTO stories (persona_id, test_run_id, story_prompts, story_themes, story_content, story_length, metadata)
            VALUES (%s, %s, %s, %s, NULL, NULL, NULL)
            RETURNING story_id;
        """, (persona_id, test_run_id, prompt, json.dumps(story_themes)))

        result = cur.fetchone()  # Fetch the new story_id safely

        if result:
            story_id = result[0]
            conn.commit()
            logger.info(f"Successfully stored story prompt. story_id={story_id}")
        else:
            logger.error(f"Failed to retrieve story_id after insertion for persona_id={persona_id}, test_run_id={test_run_id}")
            story_id = None

        cur.close()
        conn.close()
        return story_id
    except Exception as e:
        logger.error(f"Error storing story prompt: {e}")
        return None, None  # Return None if insertion fails


def store_story(test_run_id, persona_id, story_id, story, metadata):
    """
    Update the generated story content in the database.

    Args:
        test_run_id (int): The test run ID.
        persona_id (int): The persona ID.
        story_id (int): The story ID from the initial insert.
        story (str): The generated story content.
        metadata (dict): Metadata for the API call.
    """
    try:
        if story_id is None:
            logger.error(f"Cannot store story: story_id is None for persona_id={persona_id}, test_run_id={test_run_id}")
            return

        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # If test_run_id is None, don't use it in the WHERE clause
        if test_run_id:
            cur.execute("""
                UPDATE stories
                SET story_content = %s, story_length = %s, metadata = %s
                WHERE story_id = %s AND persona_id = %s AND test_run_id = %s;
            """, (story, len(story.split()), json.dumps(metadata), story_id, persona_id, test_run_id))
        else:
            cur.execute("""
                UPDATE stories
                SET story_content = %s, story_length = %s, metadata = %s
                WHERE story_id = %s AND persona_id = %s;
            """, (story, len(story.split()), json.dumps(metadata), story_id, persona_id))

        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Successfully stored story for persona_id={persona_id}, test_run_id={test_run_id}, story_id={story_id}")
    except Exception as e:
        logger.error(f"Error storing story content: {e}")

# Story Generation Function
def generate_story(test_run_id, persona_id):
    """
    Generate a day-in-the-life story based on persona details.

    Args:
        test_run_id (int): The test run ID.
        persona_id (int): The persona ID.

    Returns:
        str: Generated story content.
    """
    # Step 1: Build Persona Profile
    persona_data = build_persona_profile(logger, persona_id, test_run_id)
    if not persona_data:
        return "No persona data available."

    # Step 2: Extract and Prioritize Relevant Details
    primary_theme = persona_data["primary_theme"]
    secondary_themes = persona_data["secondary_themes"]
    passion_scores = persona_data["passion_scores"]  # Use passion scores
    input_details = persona_data["inputs"]
    foundation = persona_data["foundation"]  # Get foundation data

    # **Step 2.1: Select the Most Passionate Inputs**
    top_passionate_inputs = sorted(
        input_details, key=lambda x: passion_scores.get(x["input_id"], 0), reverse=True
    )[:3]  # Keep top 3 most passionate responses

    # **Step 2.2: Format the Inputs Cleanly**
    key_details = []
    for input_data in top_passionate_inputs:
        response_text = input_data["response_text"]
        theme = input_data["prompt_theme"]
        key_details.append(f"- {theme}: {response_text}")

    # **Step 2.3: Structure Story Themes**
    story_themes = {
        "primary_theme": primary_theme,
        "secondary_themes": secondary_themes
    }

    # **Step 3: Define Story Structure**
    day_types = ["Routine", "Adventure", "Work/Productivity", "Social", "Challenges", "Relaxation", "Vacation"]
    events = ["A major breakthrough", "A surprise visit", "A reflective moment", "A minor setback", "A celebration",]
    special_moments = ["A deep conversation", "An unexpected joy", "A lesson learned", "A moment of gratitude", "A moment of pride"]

    day_type = random.choice(day_types)
    event = random.choice(events)
    special_moment = random.choice(special_moments)

    # **Step 4: Construct the Prompt**
    prompt_chunks = [
        f"Primary story theme: {primary_theme}",
        f"Secondary story themes: {', '.join(secondary_themes)}",
        f"User's Most Passionate Inputs:\n" + "\n".join(key_details),
        f"Write a detailed narrative of their {day_type.lower()} day, incorporating {event} and {special_moment}. Include:",
        "- Sensory details (sights, sounds, smells, etc.).",
        "- Emotional moments (gratitude, joy, resilience, etc.).",
        "- Interactions with consistent characters (friends, family, colleagues, pets, etc.).",
        "- Activities that reflect their environment, goals, and values.",
        "The story should be told as if you're telling the person about their day because youwere there with them.",
        "Ensure the story flows naturally, integrating their passions while weaving in the ordinary magic of their world.",
        f"Be sure to incorporate details about the person whose story you are telling. The person whose story you are telling is named {foundation['name']}, age {foundation['age']}, who uses {foundation['pronoun']} pronouns. " 
        f"They live {foundation['location']}, are {foundation['relationship']}, {foundation['children']}, and have {foundation['pets']}."
    ]

    # **Step 5: Shuffle Prompt Components for Natural Variability**
    prompt = shuffle_prompt_components(prompt_chunks)

    # **Step 6: Store the Prompt**
    story_id = store_story_prompts(test_run_id, persona_id, prompt, story_themes)
    if not story_id:
        logger.error(f"Failed to store story prompt for persona_id={persona_id}, test_run_id={test_run_id}")
        return "Error: Story prompt not stored."

    # **Step 7: Call OpenAI API**
    metadata = {
        "model": "gpt-4",
        "system_content": "You are a vivid and emotionally resonant storyteller.",
        "max_tokens": 1500,
        "temperature": 0.8
    }
    try:
        response = client.chat.completions.create(
            model=metadata["model"],
            messages=[
                {"role": "system", "content": metadata["system_content"]},
                {"role": "user", "content": prompt}
            ],
            max_tokens=metadata["max_tokens"],
            temperature=metadata["temperature"]
        )
        story = response.choices[0].message.content.strip()
        
        # **Step 8: Store Generated Story**
        store_story(test_run_id, persona_id, story_id, story, metadata)
        return story
    except Exception as e:
        logger.error(f"Error generating story: {e}")
        return "An error occurred while generating the story."

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Generate stories for a test run')
    parser.add_argument('test_run_id', type=str, help='The test run ID to generate stories for')
    
    args = parser.parse_args()
    
    # Use the existing DB_CONFIG from config
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Get persona_id from test_run_id
        cur.execute("SELECT persona_id FROM personas WHERE test_run_id = %s", (args.test_run_id,))
        result = cur.fetchone()
        
        if not result:
            print(f"Error: No persona found for test_run_id {args.test_run_id}")
            sys.exit(1)
            
        persona_id = result[0]
        
        # Generate the story
        story = generate_story(args.test_run_id, persona_id)
        print("Story generated successfully")
        sys.exit(0)
    except Exception as e:
        print(f"Error generating story: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
