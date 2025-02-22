from transformers import BertTokenizer, BertModel
import torch
from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np
import json
import logging
from config import DB_CONFIG, LOGGING_CONFIG

# Configure logging from config.py
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Load BERT model and tokenizer
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = BertModel.from_pretrained("bert-base-uncased")

# Construct the database connection string using DB_CONFIG
DATABASE_URL = f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
engine = create_engine(DATABASE_URL)

def calculate_alignment_with_bert(story, core_values):
    """
    Calculates semantic similarity between the story and core values using BERT embeddings.

    Args:
        story (str): The story content.
        core_values (str): The core values text.

    Returns:
        float: The cosine similarity score between the story and core values.
    """
    def embed_text(text):
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
        outputs = model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).detach().numpy()

    try:
        # Generate embeddings
        story_embedding = embed_text(story)
        core_values_embedding = embed_text(core_values)
        
        # Compute cosine similarity
        cosine_similarity = np.dot(story_embedding, core_values_embedding.T) / (
            np.linalg.norm(story_embedding) * np.linalg.norm(core_values_embedding)
        )
        return float(cosine_similarity[0][0])  # Convert to Python float
    except Exception as e:
        logger.error(f"Error calculating alignment with BERT: {e}")
        raise

def update_alignment_scores():
    """
    Fetches stories and core values, calculates alignment, and updates the database.
    """
    with engine.connect() as conn:
        try:
            # Fetch stories and core values
            query = """
            SELECT stories.story_id, stories.story_content, personas.input_detail
            FROM stories
            JOIN personas ON stories.persona_id = personas.persona_id
            WHERE stories.alignment_score IS NULL
            """
            stories_data = pd.read_sql_query(query, conn)

            logger.info(f"Fetched {len(stories_data)} stories to calculate alignment scores.")

            # Calculate alignment scores
            for _, row in stories_data.iterrows():
                story_id = row["story_id"]
                story_content = row["story_content"]
                input_detail = row["input_detail"]

                # Parse input_detail if it's JSON formatted
                if isinstance(input_detail, str):
                    input_detail = json.loads(input_detail)

                core_values = input_detail.get("core_values", "")
                if not core_values:
                    logger.warning(f"No core values found for story ID {story_id}. Skipping.")
                    continue

                logger.info(f"Calculating alignment for Story ID: {story_id}")

                try:
                    alignment_score = calculate_alignment_with_bert(story_content, core_values)
                    logger.debug(f"Alignment Score for Story ID {story_id}: {alignment_score}")

                    # Update database
                    update_query = text("""
                    UPDATE stories
                    SET alignment_score = :alignment
                    WHERE story_id = :story_id
                    """)
                    conn.execute(update_query, {"alignment": alignment_score, "story_id": story_id})

                except Exception as e:
                    logger.error(f"Error calculating or updating alignment for story ID {story_id}: {e}")
                    continue

            conn.commit()
            logger.info("Alignment scores updated successfully.")
        except Exception as e:
            logger.error(f"Error in update_alignment_scores: {e}")
            raise

if __name__ == "__main__":
    logger.info("Starting alignment score updates using BERT...")
    update_alignment_scores()
    logger.info("Alignment score updates complete.")