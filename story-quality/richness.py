import pandas as pd
from sqlalchemy import create_engine, text
from gensim.models import KeyedVectors
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging
from config import DB_CONFIG, LOGGING_CONFIG, GLOVE_PATH

# Configure logging from config.py
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Construct the database connection string using DB_CONFIG
DATABASE_URL = f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
engine = create_engine(DATABASE_URL)

# Load GloVe embeddings
logger.info(f"Loading GloVe model from: {GLOVE_PATH}")
glove_model = KeyedVectors.load_word2vec_format(GLOVE_PATH, binary=False)

def calculate_richness_with_embeddings(story):
    """
    Calculates richness based on semantic diversity using GloVe embeddings.

    Args:
        story (str): The story content.

    Returns:
        float: Richness score, representing semantic diversity of the story.
    """
    try:
        words = story.split()
        unique_words = set(words)

        # Get embeddings for each unique word
        embeddings = [glove_model[word] for word in unique_words if word in glove_model]

        if len(embeddings) < 2:
            logger.warning("Not enough words for meaningful richness calculation.")
            return 0  # Not enough words for meaningful calculation

        # Compute pairwise cosine similarity
        similarity_matrix = cosine_similarity(embeddings)
        diversity_score = 1 - np.mean(similarity_matrix)  # Higher diversity = richer content
        return diversity_score
    except Exception as e:
        logger.error(f"Error calculating richness: {e}")
        raise

def update_richness_scores():
    """
    Fetches stories, calculates richness, and updates the database.
    """
    with engine.connect() as conn:
        try:
            # Fetch stories with NULL richness_score
            query = """
            SELECT story_id, story_content
            FROM stories
            WHERE richness_score IS NULL
            """
            stories_data = pd.read_sql_query(query, conn)
            logger.info(f"Fetched {len(stories_data)} stories to calculate richness scores.")

            # Calculate and update richness scores
            for _, row in stories_data.iterrows():
                story_id = row["story_id"]
                story_content = row["story_content"]

                try:
                    richness_score = calculate_richness_with_embeddings(story_content)
                    logger.debug(f"Story ID: {story_id}, Richness Score: {richness_score}")

                    # Update database
                    update_query = text("""
                    UPDATE stories
                    SET richness_score = :richness
                    WHERE story_id = :story_id
                    """)
                    conn.execute(update_query, {"richness": float(richness_score), "story_id": story_id})
                except Exception as e:
                    logger.error(f"Error processing story ID {story_id}: {e}")
                    continue

            conn.commit()
            logger.info("Richness scores updated successfully.")
        except Exception as e:
            logger.error(f"Error updating richness scores: {e}")
            raise

if __name__ == "__main__":
    logger.info("Starting richness score updates...")
    update_richness_scores()
    logger.info("Richness score updates complete.")