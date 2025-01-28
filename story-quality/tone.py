from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from sqlalchemy import create_engine, text
import pandas as pd
import logging
from config import DB_CONFIG, LOGGING_CONFIG, SENTIMENT_LIB_DIR

# Configure logging from config.py
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Load the Hugging Face sentiment analysis model
MODEL_NAME = SENTIMENT_LIB_DIR  # Use model directory from config
logger.info(f"Loading sentiment analysis model: {MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)

# Construct the database connection string using DB_CONFIG
DATABASE_URL = f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
engine = create_engine(DATABASE_URL)

def calculate_emotional_tone(story):
    """
    Calculates the emotional tone of a story using Hugging Face sentiment analysis.

    Args:
        story (str): The story content.

    Returns:
        float: Positive sentiment score.
    """
    try:
        inputs = tokenizer(story, return_tensors="pt", truncation=True, padding=True, max_length=512)
        outputs = model(**inputs)
        scores = torch.nn.functional.softmax(outputs.logits, dim=-1)
        positive_score = scores[0][2].item()  # Index 2 corresponds to positive sentiment in this model
        return positive_score
    except Exception as e:
        logger.error(f"Error calculating emotional tone: {e}")
        raise

def update_emotional_tone_scores():
    """
    Fetches stories, calculates emotional tone, and updates the database.
    """
    with engine.connect() as conn:
        try:
            # Fetch stories with NULL emotional_tone_score
            query = """
            SELECT story_id, story_content
            FROM stories
            WHERE emotional_tone_score IS NULL
            """
            stories_data = pd.read_sql_query(query, conn)
            logger.info(f"Fetched {len(stories_data)} stories to calculate emotional tone scores.")

            # Calculate and update emotional tone scores
            for _, row in stories_data.iterrows():
                story_id = row["story_id"]
                story_content = row["story_content"]

                try:
                    tone_score = calculate_emotional_tone(story_content)
                    logger.debug(f"Story ID: {story_id}, Tone Score: {tone_score}")

                    # Update database
                    update_query = text("""
                    UPDATE stories
                    SET emotional_tone_score = :tone
                    WHERE story_id = :story_id
                    """)
                    conn.execute(update_query, {"tone": tone_score, "story_id": story_id})
                except Exception as e:
                    logger.error(f"Error processing story ID {story_id}: {e}")
                    continue

            conn.commit()
            logger.info("Emotional tone scores updated successfully.")
        except Exception as e:
            logger.error(f"Error updating emotional tone scores: {e}")
            raise

if __name__ == "__main__":
    logger.info("Starting emotional tone score updates using Hugging Face sentiment analysis...")
    update_emotional_tone_scores()
    logger.info("Emotional tone score updates complete.")