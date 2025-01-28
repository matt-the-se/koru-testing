import os
import psycopg2
import time
import json
import argparse
import logging
from openai import OpenAI
from config import setup_logger, DB_CONFIG, LOGS_DIR, OPENAI_API_KEY

# Configure logging from config.py
INPUT_CLASSIFIER_LOG = os.path.join(LOGS_DIR, "generate_stories.log")
logger = setup_logger("generate_stories", INPUT_CLASSIFIER_LOG)

# Set up the OpenAI client using API key from config.py
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_story(persona):
    """
    Generate a day-in-the-life story based on persona details using OpenAI.

    Args:
        persona (dict): Persona details, including value preferences and input details.

    Returns:
        str: Generated story content.
    """
    value_preferences = persona["value_preferences"]
    input_detail = persona["input_detail"]

    prompt = f"""
    Imagine you are helping someone visualize their ideal life as part of a manifestation exercise. 
    This person has shared detailed information about their best self and the life they want to live. 

    Using the following details:
    - Value priorities: Relationships ({value_preferences['relationships']}%), Career ({value_preferences['career']}%), 
      Hobbies ({value_preferences['hobbies']}%), Health ({value_preferences['health']}%), and Spirituality ({value_preferences['spirituality']}%).
    - Personal details: 
      - Core Values: {input_detail['core_values']}
      - Vision of Success: {input_detail['vision_of_success']}
      - Morning Routine: {input_detail['morning_routine']}

    Write a detailed, emotionally resonant description of a single day in their life, highlighting their ideal routines, 
    relationships, and activities. Ensure the narrative reflects their values and aspirations, and include a mix of predictable and spontaneous moments.

    Make the story vivid and engaging, using sensory details and emotional depth to bring it to life.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a creative and vivid storyteller."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating story: {e}")
        raise

def show_progress(current, total, start_time):
    """
    Display an ASCII progress bar with stats and percentages.

    Args:
        current (int): Current progress count.
        total (int): Total number of tasks.
        start_time (float): Time when the process started.
    """
    bar_length = 50
    filled_length = int(bar_length * current / total)
    empty_length = bar_length - filled_length
    bar = '#' * filled_length + '-' * empty_length
    percentage = (current / total) * 100
    elapsed_time = time.time() - start_time
    elapsed_minutes = int(elapsed_time // 60)
    elapsed_seconds = int(elapsed_time % 60)

    print(f"\rProgress: [{bar}] {current}/{total} - {percentage:.2f}% complete. Elapsed time: {elapsed_minutes}m {elapsed_seconds}s", end="", flush=True)

def main():
    """
    Main entry point for generating stories for personas.
    """
    parser = argparse.ArgumentParser(description="Generate stories for personas.")
    parser.add_argument("--test-run-id", type=int, help="Specify an existing test run ID to use.")
    args = parser.parse_args()

    try:
        # Connect to the PostgreSQL database using DB_CONFIG from config.py
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # Determine test run ID
        if args.test_run_id:
            test_run_id = args.test_run_id
            logger.info(f"Reusing existing test run with ID: {test_run_id}")
        else:
            cur.execute("""
                INSERT INTO test_runs (description, model_used, parameters, cost)
                VALUES (%s, %s, %s, %s)
                RETURNING test_run_id;
            """, ("New test run", "gpt-4", json.dumps({"temperature": 0.7, "max_tokens": 1500}), 0))
            test_run_id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"Created new test run with ID: {test_run_id}")

        # Retrieve personas that need stories
        cur.execute("""
            SELECT p.persona_id, p.value_preferences, p.input_detail
            FROM personas p
            LEFT JOIN stories s ON p.persona_id = s.persona_id
            WHERE p.test_run_id = %s AND s.persona_id IS NULL;
        """, (test_run_id,))
        personas = cur.fetchall()

        total_personas = len(personas)
        if total_personas == 0:
            logger.info("No personas found that need stories. Exiting.")
            return

        start_time = time.time()
        for index, persona in enumerate(personas, start=1):
            persona_id = persona[0]
            value_preferences = json.loads(persona[1]) if isinstance(persona[1], str) else persona[1]
            input_detail = json.loads(persona[2]) if isinstance(persona[2], str) else persona[2]

            # Generate a story for the persona
            story = generate_story({"value_preferences": value_preferences, "input_detail": input_detail})

            # Insert the story into the database
            cur.execute("""
                INSERT INTO stories (persona_id, story_content, test_run_id)
                VALUES (%s, %s, %s);
            """, (persona_id, story, test_run_id))

            # Update progress bar
            show_progress(index, total_personas, start_time)

            # Commit after every story
            conn.commit()

        logger.info("Story generation complete.")
    except Exception as e:
        logger.error(f"Error during story generation process: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()