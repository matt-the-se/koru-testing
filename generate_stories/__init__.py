from .generate_stories import generate_story
from config import generate_stories_logger as logger

def generate_stories_for_persona(persona_id: int, test_run_id: int) -> dict:
    """
    Generate stories for a specific persona and test run.
    This is the main entry point for webapp integration.
    
    Args:
        persona_id: ID of the persona to generate stories for
        test_run_id: ID of the test run
        
    Returns:
        dict: Results of story generation including status and any error messages
    """
    try:
        logger.info(f"Starting story generation for persona {persona_id}, test run {test_run_id}")
        
        # Call generate_story() directly instead of main()
        story = generate_story(test_run_id, persona_id)
        
        if story == "No persona data available.":
            return {
                "status": "error",
                "error": "No persona data available"
            }
        elif story.startswith("Error:"):
            return {
                "status": "error",
                "error": story[7:]  # Remove "Error: " prefix
            }
            
        return {
            "status": "success",
            "data": {
                "story": story
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating stories: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
