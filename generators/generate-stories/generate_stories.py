import random
from openai import OpenAI
from config import OPENAI_API_KEY, story_logger
from theme_prioritizer import prioritize_themes

# Initialize OpenAI client
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

# Story Generation Function
def generate_story(persona_data):
    """
    Generate a day-in-the-life story based on persona details.

    Args:
        persona_data (dict): Persona details including themes, input data, and preferences.

    Returns:
        str: Generated story content.
    """
    # Step 1: Prioritize Themes
    thresholds = {
        "CHUNK_CONFIDENCE_THRESHOLD": 0.4,
        "OVERALL_CONFIDENCE_THRESHOLD": 0.6,
        "PROBABLE_THEME_BOOST": 1.1
    }
    prioritized_themes = prioritize_themes(persona_data, thresholds)

    # Extract relevant details
    primary_theme = prioritized_themes["primary_theme"]
    secondary_themes = prioritized_themes["secondary_themes"]
    all_themes = list(prioritized_themes["adjusted_weights"].keys())
    other_themes = [theme for theme in all_themes if theme not in {primary_theme, *secondary_themes}]
    input_details = persona_data.get("input_details", {})

    # Step 2: Determine the Day Type
    day_types = ["Routine", "Adventure", "Work/Productivity", "Social", "Challenges"]
    day_type = random.choice(day_types)

    # Step 3: Define Prompt Chunks
    prompt_chunks = [
        f"Primary Theme: {primary_theme}",
        f"Secondary Themes: {', '.join(secondary_themes)}",
        f"Other Aspects: Focus on additional elements such as {', '.join(other_themes)}.",
        f"Specific Inputs:\n  - Core Values: {input_details.get('core_values', 'N/A')}\n  - Actualization: {input_details.get('actualization', 'N/A')}\n  - Keywords/Details: {input_details.get('keyword_matches', 'N/A')}",
        f"Write a detailed narrative of their {day_type.lower()} day. Include:\n- A balance of major and subtle moments.\n- Sensory details (sights, sounds, smells, etc.).\n- Emotional moments (gratitude, joy, resilience, etc.).\n- Interactions with consistent characters (friends, family, colleagues, pets, etc.).\n- Varied activities that reflect their routines, environment, and goals.",
        "Ensure the story flows naturally from morning to evening, integrating their primary themes while weaving in other aspects of their life for depth and authenticity. Highlight both the extraordinary and the everyday magic of their ideal world."
    ]

    # Step 4: Shuffle Prompt
    prompt = shuffle_prompt_components(prompt_chunks)

    # Step 5: Call OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a vivid and emotionally resonant storyteller."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.8
        )
        story = response.choices[0].message.content.strip()
        return story
    except Exception as e:
        story_logger.error(f"Error generating story: {e}")
        return "An error occurred while generating the story."

# Example Usage
def main():
    """Example workflow for generating a story."""
    # Simulated persona data (replace with actual data fetch in production)
    persona_data = {
        "input_details": {
            "core_values": "Growth, connection, and creativity.",
            "vision_of_success": "Running a thriving art business by the beach.",
            "morning_routine": "Yoga, journaling, and a cup of coffee by the ocean."
        },
        "extracted_themes": {  # Example themes (replace with actual extraction logic)
            "Career and Contribution": 0.5,
            "Lifestyle and Environment": 0.8
        }
    }

    story = generate_story(persona_data)
    print("Generated Story:")
    print(story)

if __name__ == "__main__":
    main()
