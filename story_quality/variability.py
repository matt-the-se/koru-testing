import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging
from config import DB_CONFIG, LOGGING_CONFIG

# Configure logging from config.py
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Construct the database connection string using DB_CONFIG
DATABASE_URL = f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}"
engine = create_engine(DATABASE_URL)

def calculate_variability(emotional_tone_scores):
    """
    Calculates variability as the standard deviation of emotional tone scores.

    Args:
        emotional_tone_scores (list): List of emotional tone scores.

    Returns:
        float: Variability score, or 0.0 if less than two scores are available.
    """
    try:
        return np.std(emotional_tone_scores) if len(emotional_tone_scores) > 1 else 0.0
    except Exception as e:
        logger.error(f"Error calculating variability: {e}")
        raise

def update_variability_scores():
    """
    Fetches emotional tone scores, calculates variability for each persona, and updates the database.
    """
    with engine.connect() as conn:
        try:
            # Fetch personas and their emotional tone scores
            query = """
            SELECT p.persona_id, ARRAY_AGG(s.emotional_tone_score) AS tone_scores
            FROM personas p
            JOIN stories s ON p.persona_id = s.persona_id
            WHERE s.emotional_tone_score IS NOT NULL
            GROUP BY p.persona_id
            """
            personas_data = pd.read_sql_query(query, conn)
            logger.info(f"Fetched {len(personas_data)} personas for variability calculation.")

            # Calculate and update variability scores
            for _, row in personas_data.iterrows():
                persona_id = row["persona_id"]
                emotional_tone_scores = row["tone_scores"]

                try:
                    variability_score = calculate_variability(emotional_tone_scores)
                    logger.debug(f"Persona ID: {persona_id}, Variability Score: {variability_score}")

                    # Update database
                    update_query = text("""
                    UPDATE personas
                    SET variability_score = :variability
                    WHERE persona_id = :persona_id
                    """)
                    conn.execute(update_query, {"variability": variability_score, "persona_id": persona_id})
                except Exception as e:
                    logger.error(f"Error processing persona ID {persona_id}: {e}")
                    continue

            conn.commit()
            logger.info("Variability scores updated successfully.")
        except Exception as e:
            logger.error(f"Error updating variability scores: {e}")
            raise

if __name__ == "__main__":
    logger.info("Starting variability score updates...")
    update_variability_scores()
    logger.info("Variability score updates complete.")