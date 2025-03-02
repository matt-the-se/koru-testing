# Import the new implementation
from .generate_stories import generate_story
from config import generate_stories_logger as logger

def generate_stories_for_persona(persona_id=None, test_run_id=None):
    """
    Generate stories for a specific persona and test run.
    This is the main entry point for webapp integration.
    
    Args:
        persona_id: Optional ID of the persona to generate stories for. If not provided, it will be looked up from test_run_id.
        test_run_id: ID of the test run. Required.
        
    Returns:
        dict: Results of story generation including status and any error messages
    """
    try:
        if test_run_id is None:
            return {
                "status": "error",
                "error": "test_run_id is required"
            }
            
        logger.info(f"Starting story generation for test run {test_run_id}" + 
                   (f", persona {persona_id}" if persona_id else ""))
        
        # Using the new implementation
        result = generate_story(test_run_id, persona_id)
        
        if isinstance(result, str) and result.startswith("Error:"):
            return {
                "status": "error",
                "error": result[7:]  # Remove "Error: " prefix
            }
            
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"Error generating stories: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
