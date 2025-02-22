from enum import Enum
from typing import List, Dict, List, Optional, Tuple
from dataclasses import dataclass
import json
import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import (
    DB_CONFIG, 
    WEBAPP_DB_CONFIG, 
    SQLALCHEMY_DATABASE_URL,
    input_processing_logger as logger
)
from .models import Base, TestRun, PersonaInput, Prompt
from datetime import datetime
from flask import current_app

class DBEnvironment(Enum):
    """Enum for different database environments"""
    WEBAPP = 'webapp'
    TESTING = 'testing'
    GENERATORS = 'generators'

@dataclass
class TestRun:
    """Represents a complete test run with all inputs"""
    test_run_id: int
    persona_id: Optional[int]
    inputs: List[Dict]
    status: str

@dataclass
class PromptResponse:
    """Represents a single prompt response with its metadata"""
    input_id: int
    prompt_id: int
    response_text: str
    extracted_themes: Optional[Dict] = None
    clarity_score: Optional[float] = None
    probable_theme: Optional[str] = None

class DatabaseManager:
    def __init__(self, environment: DBEnvironment):
        self.environment = environment
        self.connection = psycopg2.connect(**DB_CONFIG)
        self.config = self._load_config()
        self.logger = logger
        
        # Set up SQLAlchemy for webapp
        if environment == DBEnvironment.WEBAPP:
            self.engine = create_engine(SQLALCHEMY_DATABASE_URL)
            self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables for SQLAlchemy if in webapp mode
        if environment == DBEnvironment.WEBAPP:
            Base.metadata.create_all(bind=self.engine)
        
    def _load_config(self) -> Dict:
        """Load appropriate database configuration"""
        if self.environment == DBEnvironment.WEBAPP:
            return WEBAPP_DB_CONFIG
        return DB_CONFIG

    def get_connection(self):
        """Get a database connection with proper error handling"""
        try:
            conn = psycopg2.connect(**self.config)
            conn.autocommit = True  # Prevent transaction issues
            return conn
        except Exception as e:
            self.logger.error(f"Error connecting to database: {e}")
            raise

    @contextmanager
    def get_session(self):
        """SQLAlchemy session for webapp"""
        if self.config != WEBAPP_DB_CONFIG:
            raise ValueError("SQLAlchemy sessions only available in webapp environment")
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def create_test_run(self) -> int:
        """Create a new test run and return its ID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO test_runs (status) VALUES ('initialized') RETURNING test_run_id"
                    )
                    test_run_id = cur.fetchone()[0]
                    conn.commit()
                    self.logger.info(f"Created new test run with ID: {test_run_id}")
                    return test_run_id
        except Exception as e:
            self.logger.error(f"Error creating test run: {e}")
            raise

    def store_prompt_response(self, test_run_id: int, prompt_id: int, persona_id: int, response_text: str, variation_id: Optional[int] = None) -> int:
        """Store a prompt response and return the input_id"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    user_prefs = {
                        "prompt_id": prompt_id,
                        "variation_id": variation_id if variation_id != 0 else None,
                        "section": "core_vision",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    cur.execute("""
                        INSERT INTO persona_inputs 
                        (persona_id, prompt_id, test_run_id, response_text, user_prompt_prefs)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING input_id
                    """, (
                        persona_id, 
                        prompt_id,
                        test_run_id,
                        response_text,
                        json.dumps(user_prefs)
                    ))
                    conn.commit()
                    return cur.fetchone()[0]
                except Exception as e:
                    conn.rollback()  # Rollback on error
                    raise

    def get_test_run_inputs_raw(self, test_run_id: int) -> List[Dict]:
        """Original raw SQL method"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM persona_inputs WHERE test_run_id = %s
                """, (test_run_id,))
                return cur.fetchall()

    def get_test_run_inputs_orm(self, test_run_id: int):
        """New SQLAlchemy method for webapp"""
        if self.config != WEBAPP_DB_CONFIG:
            raise ValueError("ORM methods only available in webapp environment")
        with self.get_session() as session:
            return session.query(PersonaInput).filter_by(test_run_id=test_run_id).all()

    def update_extracted_themes(self, input_id: int, themes: Dict):
        """Update extracted themes for an input"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE persona_inputs 
                    SET extracted_themes = %s::jsonb
                    WHERE input_id = %s
                """, (json.dumps(themes), input_id))

    def get_input_data(self, test_run_id: int) -> List[PromptResponse]:
        """Get all input data for processing"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        pi.input_id,
                        pi.prompt_id,
                        pi.response_text,
                        pi.extracted_themes,
                        pi.clarity_score,
                        p.prompt_theme as probable_theme
                    FROM persona_inputs pi
                    JOIN prompts p ON pi.prompt_id = p.prompt_id
                    WHERE pi.test_run_id = %s
                    ORDER BY pi.input_id
                """, (test_run_id,))
                
                return [
                    PromptResponse(
                        input_id=row[0],
                        prompt_id=row[1],
                        response_text=row[2],
                        extracted_themes=row[3],
                        clarity_score=row[4],
                        probable_theme=row[5]
                    )
                    for row in cur.fetchall()
                ]

    def update_confidence_scores(self, input_id: int, scores: Dict[str, float]):
        """Update confidence scores for an input"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE persona_inputs 
                    SET clarity_score = %s
                    WHERE input_id = %s
                """, (json.dumps(scores), input_id))

    def create_persona_from_foundation(self, foundation_data: Dict) -> Tuple[int, int]:
        """Create persona and test run from foundation data, return (persona_id, test_run_id)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # First create test run
                    cur.execute(
                        "INSERT INTO test_runs DEFAULT VALUES RETURNING test_run_id"
                    )
                    test_run_id = cur.fetchone()[0]
                    
                    # Then create persona with foundation
                    cur.execute("""
                        INSERT INTO personas 
                        (foundation, detail_level, test_run_id)
                        VALUES (%s, %s, %s)
                        RETURNING persona_id
                    """, (
                        json.dumps(foundation_data),
                        'standard',  # or from config
                        test_run_id
                    ))
                    persona_id = cur.fetchone()[0]
                    
                    conn.commit()
                    self.logger.info(f"Created persona {persona_id} with test run {test_run_id}")
                    return persona_id, test_run_id
                
        except Exception as e:
            self.logger.error(f"Error creating persona from foundation: {e}")
            raise

    def get_persona_foundation(self, persona_id: int) -> Dict:
        """Get foundation data for a persona"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT foundation 
                    FROM personas 
                    WHERE persona_id = %s
                """, (persona_id,))
                result = cur.fetchone()
                return result[0] if result else None

    def get_available_prompts(self, section=None):
        """Get available prompts, optionally filtered by section"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT p.prompt_id, 
                           p.prompt_complete->>'prompt_text' as base_prompt,
                           p.prompt_complete->>'themes' as theme,
                           p.variations,
                           p.prompt_complete->>'section' as section
                    FROM prompts p
                    WHERE LOWER(p.prompt_complete->>'section') = LOWER(%s)
                      AND p.prompt_type = 'structured_prompts'
                    ORDER BY p.prompt_id
                """
                cur.execute(query, (section,) if section else ('Core Vision',))
                prompts = []
                for row in cur.fetchall():
                    # Extract variation texts from the variations array
                    variation_texts = []
                    if row[3]:  # if variations exist
                        for var in row[3]:
                            variation_texts.append(var['text'])

                    prompts.append({
                        'prompt_id': row[0],
                        'base_prompt': row[1],
                        'theme': row[2],
                        'variations': variation_texts,
                        'section': row[4]
                    })
                self.logger.debug(f"Found prompts: {prompts}")
                return prompts

    def update_clarity_scores(self, test_run_id: int, clarity_scores: dict) -> bool:
        """Update clarity scores for a test run"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("""
                        UPDATE personas
                        SET clarity_scores = %s::jsonb
                        WHERE test_run_id = %s
                    """, (json.dumps(clarity_scores), test_run_id))
                    conn.commit()
                    return True
                except Exception as e:
                    conn.rollback()
                    current_app.logger.error(f"Error updating clarity scores: {e}")
                    return False

    def get_clarity_scores(self, test_run_id: int) -> dict:
        """Get clarity scores for a test run"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("""
                        SELECT clarity_scores 
                        FROM personas 
                        WHERE test_run_id = %s
                    """, (test_run_id,))
                    result = cur.fetchone()
                    return result[0] if result else {}
                except Exception as e:
                    current_app.logger.error(f"Error getting clarity scores: {e}")
                    return {}

    def set_foundation_clarity(self, test_run_id: int, clarity_scores: dict = None):
        """Set initial clarity score after foundation creation"""
        if clarity_scores is None:
            clarity_scores = {
                "overall": 0.0,
                "sections": {
                    "core_vision": 0.0,
                    "actualization": 0.0,
                    "freeform": 0.0
                },
                "themes": {},
                "foundation_complete": True
            }
        return self.update_clarity_scores(test_run_id, clarity_scores)

    def get_clarity_status(self, test_run_id: int) -> Dict:
        """Get current clarity scores and section availability"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT p.persona_id, p.clarity_scores,
                           COUNT(pi.input_id) as input_count
                    FROM personas p
                    LEFT JOIN persona_inputs pi ON p.persona_id = pi.persona_id
                    WHERE p.test_run_id = %s
                    GROUP BY p.persona_id, p.clarity_scores
                """, (test_run_id,))
                result = cur.fetchone()
                
                if not result:
                    return None
                    
                persona_id, scores, input_count = result
                
                # Default structure if no scores yet
                if not scores:
                    scores = {
                        "overall": 0.0,
                        "sections": {
                            "core_vision": 0.0,
                            "actualization": 0.0,
                            "freeform": 0.0
                        },
                        "themes": {}
                    }
                
                return {
                    "clarity_scores": scores,
                    "sections_available": {
                        "core_vision": True,
                        "actualization": scores["sections"]["core_vision"] >= 0.4,  # Your threshold
                        "freeform": True
                    },
                    "pipeline_status": {
                        "foundation_complete": scores.get("foundation_complete", False),
                        "inputs_processed": input_count,
                        "themes_extracted": bool(scores.get("themes")),
                        "clarity_calculated": bool(scores.get("overall"))
                    }
                } 

    def update_prompt_preference(self, input_id: int, preference_data: Dict) -> Dict:
        """Update user's prompt preference for a given input
        
        Args:
            input_id: ID of the persona_input
            preference_data: Dict containing:
                - prompt_id: int
                - selection_type: str ('base_prompt' or 'variation')
                - variation_id: Optional[int]
                - reason: Optional[str]
        
        Returns:
            Dict containing the stored preference data with timestamp
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # First verify the input exists
                    cur.execute("""
                        SELECT persona_id, prompt_id 
                        FROM persona_inputs 
                        WHERE input_id = %s
                    """, (input_id,))
                    
                    result = cur.fetchone()
                    if not result:
                        raise ValueError(f"Input ID {input_id} not found")
                    
                    persona_id, existing_prompt_id = result
                    
                    # Verify prompt_id matches
                    if preference_data['prompt_id'] != existing_prompt_id:
                        raise ValueError("Prompt ID mismatch")
                    
                    # Build preference JSON
                    pref_json = {
                        "prompt_id": preference_data['prompt_id'],
                        "selection_type": preference_data['selection_type'],
                        "recorded_at": datetime.utcnow().isoformat()
                    }
                    
                    # Add optional fields
                    if preference_data.get('variation_id'):
                        pref_json['variation_id'] = preference_data['variation_id']
                    if preference_data.get('reason'):
                        pref_json['reason'] = preference_data['reason']
                    
                    # Update the preference
                    cur.execute("""
                        UPDATE persona_inputs 
                        SET user_prompt_prefs = %s::jsonb
                        WHERE input_id = %s
                        RETURNING user_prompt_prefs
                    """, (json.dumps(pref_json), input_id))
                    
                    stored_prefs = cur.fetchone()[0]
                    conn.commit()
                    
                    self.logger.info(f"Updated prompt preference for input {input_id}")
                    return stored_prefs
                    
        except Exception as e:
            self.logger.error(f"Error updating prompt preference: {e}")
            raise

    def get_prompt_preferences(self, persona_id: Optional[int] = None) -> List[Dict]:
        """Get prompt preferences, optionally filtered by persona
        
        Useful for analytics and prompt optimization
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT pi.input_id, pi.persona_id, pi.prompt_id, 
                           pi.user_prompt_prefs, p.prompt_text
                    FROM persona_inputs pi
                    JOIN prompts p ON pi.prompt_id = p.prompt_id
                    WHERE pi.user_prompt_prefs IS NOT NULL
                """
                params = []
                
                if persona_id:
                    query += " AND pi.persona_id = %s"
                    params.append(persona_id)
                    
                cur.execute(query, params)
                
                return [
                    {
                        "input_id": row[0],
                        "persona_id": row[1],
                        "prompt_id": row[2],
                        "preferences": row[3],
                        "prompt_text": row[4]
                    }
                    for row in cur.fetchall()
                ] 

    def get_theme_keywords(self) -> Dict[str, List[str]]:
        """Get keywords/tags organized by theme"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT theme, tags
                    FROM tags
                    WHERE tags IS NOT NULL
                """)
                return {
                    row[0]: row[1]  # theme: list of tags
                    for row in cur.fetchall()
                }

    def update_keyword_matches(self, test_run_id: int, matches: Dict):
        """Update keyword matches for a test run"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE persona_inputs
                    SET keyword_matches = %s::jsonb
                    WHERE test_run_id = %s
                """, (json.dumps(matches), test_run_id))
                conn.commit()

    def reset_keyword_matches(self, test_run_id: int):
        """Reset keyword matches for a test run"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE persona_inputs
                    SET keyword_matches = NULL
                    WHERE test_run_id = %s
                """, (test_run_id,))
                conn.commit()

    def update_passion_scores(self, persona_id: int, scores: Dict[str, float]):
        """Store computed passion scores for a persona's inputs"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE persona_inputs
                    SET passion_scores = %s::jsonb
                    WHERE persona_id = %s
                """, (json.dumps(scores), persona_id))
                conn.commit()

    def get_persona_profile(self, persona_id: int, test_run_id: Optional[int] = None) -> Dict:
        """Get complete persona profile including inputs, themes, and passion scores"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # First get test_run_id if not provided
                if not test_run_id:
                    cur.execute("""
                        SELECT test_run_id FROM personas 
                        WHERE persona_id = %s
                    """, (persona_id,))
                    test_run_id = cur.fetchone()[0]

                # Get all persona data
                cur.execute("""
                    SELECT 
                        p.foundation,
                        pi.input_id,
                        pi.prompt_id,
                        pi.response_text,
                        pi.extracted_themes,
                        pi.passion_scores,
                        pr.prompt_theme
                    FROM personas p
                    JOIN persona_inputs pi ON p.persona_id = pi.persona_id
                    JOIN prompts pr ON pi.prompt_id = pr.prompt_id
                    WHERE p.persona_id = %s
                """, (persona_id,))
                
                rows = cur.fetchall()
                if not rows:
                    return None

                # Get theme statistics
                cur.execute("""
                    SELECT 
                        jsonb_object_agg(
                            prompt_theme,
                            confidence_score
                        ) as theme_confidences
                    FROM (
                        SELECT 
                            p.prompt_theme,
                            AVG((pi.extracted_themes->'response_text'->'confidence'->p.prompt_theme)::float) as confidence_score
                        FROM persona_inputs pi
                        JOIN prompts p ON pi.prompt_id = p.prompt_id
                        WHERE pi.persona_id = %s
                        GROUP BY p.prompt_theme
                    ) theme_scores
                """, (persona_id,))
                
                theme_data = cur.fetchone()[0] or {}

                # Structure the data
                foundation = rows[0][0]
                inputs = [
                    {
                        "input_id": row[1],
                        "prompt_id": row[2],
                        "response_text": row[3],
                        "extracted_themes": row[4],
                        "passion_scores": row[5],
                        "prompt_theme": row[6]
                    }
                    for row in rows
                ]

                # Sort themes by confidence
                sorted_themes = sorted(
                    theme_data.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )

                return {
                    "persona_id": persona_id,
                    "test_run_id": test_run_id,
                    "foundation": foundation,
                    "inputs": inputs,
                    "theme_confidences": theme_data,
                    "primary_theme": sorted_themes[0][0] if sorted_themes else None,
                    "secondary_themes": [t[0] for t in sorted_themes[1:3]] if len(sorted_themes) > 1 else []
                } 

    def store_story_prompt(self, test_run_id: int, persona_id: int, prompt: str, themes: Dict) -> int:
        """Store generated story prompt and return story_id"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO stories 
                    (persona_id, test_run_id, story_prompts, story_themes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING story_id
                """, (persona_id, test_run_id, prompt, json.dumps(themes)))
                story_id = cur.fetchone()[0]
                conn.commit()
                return story_id

    def update_story_content(self, story_id: int, content: str, metadata: Dict):
        """Update story with generated content and metadata"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE stories
                    SET story_content = %s,
                        story_length = %s,
                        metadata = %s
                    WHERE story_id = %s
                """, (content, len(content.split()), json.dumps(metadata), story_id))
                conn.commit()

    def update_input_classifications(self, test_run_id: int, classifications: Dict):
        """Update input classifications for a test run"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE persona_inputs
                    SET classifications = %s::jsonb
                    WHERE test_run_id = %s
                """, (json.dumps(classifications), test_run_id))
                conn.commit()

    def get_saved_responses(self, test_run_id: int, section: str) -> Dict:
        """Get saved responses for a test run and section"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT pi.prompt_id, pi.variation_id, pi.response_text
                    FROM persona_inputs pi
                    JOIN prompts p ON pi.prompt_id = p.prompt_id
                    WHERE pi.test_run_id = %s 
                    AND p.prompt_complete->>'section' = %s
                """, (test_run_id, section))
                rows = cur.fetchall()
                
                return {
                    row[0]: {
                        'variation_id': row[1],
                        'response_text': row[2]
                    } for row in rows
                } 

    def store_response(self, test_run_id, persona_id, variation_id, response_text):
        """Store a response, overwriting any existing response for this combination"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # First delete any existing response for this combination
                cur.execute("""
                    DELETE FROM user_inputs 
                    WHERE test_run_id = %s 
                    AND persona_id = %s 
                    AND variation_id = %s
                """, (test_run_id, persona_id, variation_id))
                
                # Then insert the new response
                cur.execute("""
                    INSERT INTO user_inputs (test_run_id, persona_id, variation_id, response_text)
                    VALUES (%s, %s, %s, %s)
                    RETURNING input_id
                """, (test_run_id, persona_id, variation_id, response_text))
                
                input_id = cur.fetchone()[0]
                conn.commit()
                return input_id

    def update_input_chunks(self, input_id, chunks):
        """Update chunks for an input, overwriting existing chunks"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Delete existing chunks
                cur.execute("DELETE FROM input_chunks WHERE input_id = %s", (input_id,))
                
                # Insert new chunks
                for chunk in chunks:
                    cur.execute("""
                        INSERT INTO input_chunks (input_id, chunk_text, chunk_metadata)
                        VALUES (%s, %s, %s)
                    """, (input_id, chunk['text'], json.dumps(chunk.get('metadata', {}))))
                
                conn.commit()

    def get_persona_id_by_test_run(self, test_run_id):
        """Get persona_id associated with a test_run_id"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT persona_id 
                    FROM personas 
                    WHERE test_run_id = %s
                """, (test_run_id,))
                result = cur.fetchone()
                return result[0] if result else None 
    
    def get_story_content(self, test_run_id):
        """Fetch the most recent story content for a given test run ID"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT story_content, generated_at, story_id 
                        FROM stories 
                        WHERE test_run_id = %s
                        ORDER BY story_id DESC
                        LIMIT 1
                    """, (test_run_id,))
                    
                    result = cur.fetchone()
                    
                    if result is None:
                        return {"status": "pending", "content": None}
                        
                    return {
                        "status": "complete",
                        "content": result[0],
                        "generated_at": result[1],
                        "story_id": result[2]
                    }
                    
        except Exception as e:
            self.logger.error(f"Error fetching story: {e}")
            return {"status": "error", "content": None}

    def get_last_input_change(self, test_run_id):
        """Get timestamp of last input change"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT MAX(created_at)
                    FROM persona_inputs
                    WHERE test_run_id = %s
                """, (test_run_id,))
                return cur.fetchone()[0]

    def clear_story(self, test_run_id):
        """Clear the story content when inputs are updated"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    # First check if there's an existing story with content
                    cur.execute("""
                        SELECT story_id 
                        FROM stories 
                        WHERE test_run_id = %s 
                        AND story_content IS NOT NULL
                        ORDER BY story_id DESC
                        LIMIT 1
                    """, (test_run_id,))
                    
                    # Only clear if there's existing content
                    if cur.fetchone():
                        # Insert new null story to preserve history
                        cur.execute("""
                            INSERT INTO stories 
                            (test_run_id, story_content, generated_at)
                            VALUES (%s, NULL, NULL)
                        """, (test_run_id,))
                        conn.commit()
                except Exception as e:
                    conn.rollback()
                    raise

    def get_story_metadata(self, test_run_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT story_id, status, story_content, generated_at, updated_at
                    FROM stories 
                    WHERE test_run_id = %s
                    ORDER BY generated_at DESC 
                    LIMIT 1
                """, (test_run_id,))
                result = cur.fetchone()
                if result:
                    return {
                        'story_id': result[0],
                        'status': result[1],
                        'content': result[2],
                        'generated_at': result[3],
                        'updated_at': result[4]
                    }
                return None

    def store_story(self, test_run_id, persona_id, story_content, status='complete'):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO stories 
                        (test_run_id, persona_id, story_content, status, generated_at, updated_at)
                    VALUES 
                        (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    RETURNING story_id
                """, (test_run_id, persona_id, story_content, status))
                story_id = cur.fetchone()[0]
                conn.commit()
                return story_id

    def clear_story(self, test_run_id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE stories 
                    SET status = 'pending', 
                        story_content = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE test_run_id = %s
                """, (test_run_id,))
                conn.commit()