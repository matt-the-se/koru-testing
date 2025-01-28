from neo4j import GraphDatabase
from keybert import KeyBERT
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import logging
from config import NEO4J_CONFIG, LOGGING_CONFIG

# Configure logging from config.py
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

class KnowledgeGraph:
    def __init__(self, uri, username, password):
        """
        Initialize the KnowledgeGraph class with Neo4j connection and models.

        Args:
            uri (str): Neo4j URI.
            username (str): Neo4j username.
            password (str): Neo4j password.
        """
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.keybert_model = KeyBERT()
        self.bert_model = SentenceTransformer("all-MiniLM-L6-v2")

    def close(self):
        """
        Close the Neo4j database connection.
        """
        self.driver.close()

    def create_persona(self, persona_name, categories_scores):
        """
        Create a Persona node and link it to categories with scores in Neo4j.

        Args:
            persona_name (str): Name of the persona.
            categories_scores (dict): Mapping of category names to scores.
        """
        logger.info(f"Creating Persona: {persona_name}")
        with self.driver.session() as session:
            try:
                # Create Persona node
                session.run("CREATE (p:Persona {name: $name})", {"name": persona_name})

                # Create Category nodes and relationships
                for category, score in categories_scores.items():
                    query = """
                    MERGE (c:Category {name: $category})
                    WITH c
                    MATCH (p:Persona {name: $persona})
                    MERGE (p)-[:HAS_CATEGORY {score: $score}]->(c)
                    """
                    session.run(query, {"persona": persona_name, "category": category, "score": score})
            except Exception as e:
                logger.error(f"Error creating Persona '{persona_name}': {e}")
                raise

    def create_story(self, story_title, story_content, alignments):
        """
        Create a Story node and link it to categories with alignment scores in Neo4j.

        Args:
            story_title (str): Title of the story.
            story_content (str): Content of the story.
            alignments (dict): Mapping of category names to alignment scores.
        """
        logger.info(f"Creating Story: {story_title}")
        with self.driver.session() as session:
            try:
                # Create Story node
                session.run("CREATE (s:Story {title: $title, content: $content})",
                            {"title": story_title, "content": story_content})

                # Link to categories
                for category, score in alignments.items():
                    query = """
                    MERGE (c:Category {name: $category})
                    WITH c
                    MATCH (s:Story {title: $story})
                    MERGE (s)-[:ALIGNS_WITH {alignment_score: $score}]->(c)
                    """
                    session.run(query, {"story": story_title, "category": category, "score": score})
            except Exception as e:
                logger.error(f"Error creating Story '{story_title}': {e}")
                raise

    def calculate_resonance(self, persona_name, story_title):
        """
        Calculate the resonance score for a story based on a persona's profile.

        Args:
            persona_name (str): Name of the persona.
            story_title (str): Title of the story.

        Returns:
            float: Resonance score as a percentage.
        """
        logger.info(f"Calculating Resonance for Persona: {persona_name}, Story: {story_title}")
        with self.driver.session() as session:
            try:
                query = """
                MATCH (p:Persona {name: $persona})-[r:HAS_CATEGORY]->(c:Category)<-[a:ALIGNS_WITH]-(s:Story {title: $story})
                RETURN c.name AS category, r.score AS persona_score, a.alignment_score AS story_score
                """
                results = session.run(query, {"persona": persona_name, "story": story_title})

                total_score = 0
                max_score = 0
                for record in results:
                    persona_score = record["persona_score"]
                    story_score = record["story_score"]
                    total_score += persona_score * story_score
                    max_score += 10 * 10  # Assuming scores are out of 10

                resonance = (total_score / max_score) * 100 if max_score > 0 else 0
                logger.debug(f"Resonance Score: {resonance:.2f}%")
                return resonance
            except Exception as e:
                logger.error(f"Error calculating Resonance for Persona '{persona_name}', Story '{story_title}': {e}")
                raise

if __name__ == "__main__":
    logger.info("Starting KnowledgeGraph operations...")

    # Initialize the KnowledgeGraph
    kg = KnowledgeGraph(NEO4J_CONFIG["uri"], NEO4J_CONFIG["username"], NEO4J_CONFIG["password"])

    # Sample data
    persona_name = "Explorer"
    persona_categories = {
        "Foundation of Self": 8,
        "Vision of Success": 7,
        "Day-in-the-Life → Morning": 9,
        "Work and Fulfillment": 6,
    }

    story_title = "Climbing Everest"
    story_content = "An adventurous climb to the peak of Mount Everest."
    story_alignments = {
        "Foundation of Self": 8,
        "Vision of Success": 6,
        "Day-in-the-Life → Morning": 7,
    }

    try:
        # Step 1: Create Persona and Categories
        kg.create_persona(persona_name, persona_categories)

        # Step 2: Create Story and Alignments
        kg.create_story(story_title, story_content, story_alignments)

        # Step 3: Calculate Resonance
        resonance_score = kg.calculate_resonance(persona_name, story_title)
        logger.info(f"Resonance Score for '{story_title}' and Persona '{persona_name}': {resonance_score:.2f}%")
    finally:
        # Close the connection
        kg.close()
        logger.info("KnowledgeGraph operations complete.")