from typing import Dict, Any, List
import psycopg2
from psycopg2.extras import RealDictCursor
from config import generate_stories_logger as logger

# Module level config that can be overridden
_db_config = None

def set_db_config(config: Dict[str, Any]) -> None:
    """Set database configuration for this module"""
    global _db_config
    _db_config = config

def get_db_connection():
    """Get database connection using config"""
    try:
        global _db_config  # Move global declaration to top of function
        if _db_config is None:
            from config import DB_CONFIG
            _db_config = DB_CONFIG
        return psycopg2.connect(**_db_config)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

def get_foundation_data(persona_id: int) -> Dict[str, Any]:
    """Get foundation data for persona"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT foundation
                FROM personas
                WHERE persona_id = %s
            """, (persona_id,))
            
            result = cur.fetchone()
            if not result:
                raise ValueError(f"No foundation data found for persona_id {persona_id}")
            
            return result["foundation"]  # JSONB column

def get_inputs_data(test_run_id: int) -> List[Dict[str, Any]]:
    """Get all inputs with their themes and extracted data"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # First check if there are any inputs for this test_run_id
            cur.execute("""
                SELECT COUNT(*) as count
                FROM persona_inputs
                WHERE test_run_id = %s
            """, (test_run_id,))
            count_result = cur.fetchone()
            print(f"DEBUG get_inputs_data: Found {count_result['count']} inputs for test_run_id {test_run_id} (before JOIN)")
            
            # Get all inputs with prompt data for the test run
            # Only include prompts with ID >= 11 (core_vision, actualization)
            cur.execute("""
                SELECT 
                    pi.input_id,
                    pi.response_text,
                    pi.prompt_id,
                    pi.extracted_themes,
                    pi.response_stats,
                    p.prompt_theme,
                    p.prompt_complete
                FROM persona_inputs pi
                LEFT JOIN prompts p ON pi.prompt_id = p.prompt_id
                WHERE pi.test_run_id = %s AND (pi.prompt_id >= 11 OR pi.prompt_id IS NULL)
            """, (test_run_id,))
            
            results = [dict(row) for row in cur.fetchall()]
            print(f"DEBUG get_inputs_data: Found {len(results)} inputs after JOIN with prompt_id >= 11")
            
            # Process each input to ensure it has the correct theme information
            processed_results = []
            for row in results:
                print(f"DEBUG get_inputs_data: Processing input_id={row['input_id']}, prompt_id={row['prompt_id']}")
                
                # If we have extracted_themes, use those
                if row['extracted_themes']:
                    print(f"DEBUG get_inputs_data: extracted_themes keys: {list(row['extracted_themes'].keys())}")
                    
                    # Make sure prompt_theme is set correctly
                    if row['prompt_theme'] is None and row['prompt_id'] is not None:
                        # Try to get theme from prompt_themes or prompts_complete
                        if row['prompt_theme']:
                            # Extract first theme from prompt_themes
                            row['prompt_theme'] = list(row['prompt_theme'].keys())[0] if row['prompt_theme'] else 'Unknown'
                            print(f"DEBUG get_inputs_data: Set prompt_theme from prompt_themes: {row['prompt_theme']}")
                    
                    # Add the 'aggregated' field if it doesn't exist
                    if 'aggregated' not in row['extracted_themes']:
                        # Create aggregated field from response_text data if available
                        if 'response_text' in row['extracted_themes'] and row['extracted_themes']['response_text']:
                            response_data = row['extracted_themes']['response_text']
                            
                            # Create aggregated data structure
                            aggregated = {
                                'themes': {},
                                'top_themes': []
                            }
                            
                            # Add theme confidences to aggregated.themes
                            if 'confidence' in response_data and response_data['confidence']:
                                aggregated['themes'] = response_data['confidence']
                            
                            # Add top themes
                            if 'response_themes' in response_data and response_data['response_themes']:
                                aggregated['top_themes'] = response_data['response_themes']
                            elif 'top_theme' in response_data and response_data['top_theme']:
                                aggregated['top_themes'] = [response_data['top_theme']]
                            
                            # Add the aggregated field to extracted_themes
                            row['extracted_themes']['aggregated'] = aggregated
                            print(f"DEBUG get_inputs_data: Added aggregated field with themes: {list(aggregated['themes'].keys())}")
                    
                    # Add chunk_scores field to the input
                    row['chunk_scores'] = {}
                    
                    # If we have chunks in extracted_themes, use their confidences for chunk_scores
                    if 'chunks' in row['extracted_themes'] and row['extracted_themes']['chunks']:
                        chunks = row['extracted_themes']['chunks']
                        for i, chunk in enumerate(chunks):
                            if isinstance(chunk, dict) and 'confidence' in chunk:
                                row['chunk_scores'][str(i)] = chunk['confidence']
                    
                    # If no chunks with confidences, use response_text confidence as a fallback
                    if not row['chunk_scores'] and 'response_text' in row['extracted_themes']:
                        response_data = row['extracted_themes']['response_text']
                        if 'confidence' in response_data and response_data['confidence']:
                            row['chunk_scores']['0'] = response_data['confidence']
                    
                    print(f"DEBUG get_inputs_data: Added chunk_scores with {len(row['chunk_scores'])} chunks")
                    
                    processed_results.append(row)
            
            print(f"DEBUG get_inputs_data: Returning {len(processed_results)} processed inputs")
            return processed_results

def get_clarity_scores(test_run_id: int) -> Dict[str, Any]:
    """Get clarity scores for test run"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT clarity_scores
                FROM personas
                WHERE test_run_id = %s
            """, (test_run_id,))
            
            result = cur.fetchone()
            return result["clarity_scores"] if result else {}  # JSON column from personas table

def get_passion_scores(test_run_id: int) -> Dict[int, float]:
    """Get passion scores for all inputs in test run"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT pi.input_id, p.passion_scores->pi.input_id::text as passion_score
                FROM persona_inputs pi
                JOIN personas p ON p.persona_id = pi.persona_id
                WHERE pi.test_run_id = %s
            """, (test_run_id,))
            
            results = cur.fetchall()
            return {
                row["input_id"]: float(row["passion_score"]) 
                for row in results 
                if row["passion_score"] is not None
            }

def store_story(test_run_id: int, story_content: str, prompt: str, persona_id: int = None) -> None:
    """Store generated story with its prompt"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get persona_id from test_run if not provided
            if persona_id is None:
                cur.execute("""
                    SELECT persona_id 
                    FROM personas 
                    WHERE test_run_id = %s
                """, (test_run_id,))
                result = cur.fetchone()
                if result:
                    persona_id = result[0]
                else:
                    raise ValueError(f"No persona_id found for test_run_id {test_run_id}")
            
            # First check if story exists
            cur.execute("""
                SELECT story_id 
                FROM stories 
                WHERE test_run_id = %s
            """, (test_run_id,))
            
            if cur.fetchone():
                # Update existing story
                cur.execute("""
                    UPDATE stories 
                    SET story_content = %s,
                        story_prompts = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE test_run_id = %s
                """, (story_content, prompt, test_run_id))
            else:
                # Insert new story
                cur.execute("""
                    INSERT INTO stories (
                        test_run_id,
                        persona_id,
                        story_content, 
                        story_prompts,
                        created_at,
                        updated_at
                    ) VALUES (
                        %s, %s, %s, %s, 
                        CURRENT_TIMESTAMP, 
                        CURRENT_TIMESTAMP
                    )
                """, (test_run_id, persona_id, story_content, prompt))
            
            conn.commit()

def get_story_status(test_run_id: int) -> Dict[str, Any]:
    """Get story generation status and content"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    story_content,
                    story_prompts,
                    created_at,
                    updated_at
                FROM stories
                WHERE test_run_id = %s
            """, (test_run_id,))
            
            result = cur.fetchone()
            if not result:
                return {"status": "pending"}
            
            return {
                "status": "complete",
                "content": result["story_content"],
                "prompt": result["story_prompts"],
                "created_at": result["created_at"],
                "updated_at": result["updated_at"]
            }

def get_persona_id_from_test_run(test_run_id: int) -> int:
    """Get the persona_id associated with a test_run_id"""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT persona_id 
                FROM personas 
                WHERE test_run_id = %s
            """, (test_run_id,))
            
            result = cur.fetchone()
            if not result:
                raise ValueError(f"No persona_id found for test_run_id {test_run_id}")
            
            return result[0]  # Return the persona_id 