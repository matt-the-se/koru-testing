from flask import Blueprint, jsonify, request, current_app, render_template
from ..pipeline_utils import run_story_generation

bp = Blueprint('foundation', __name__, url_prefix='/api/v1')

@bp.route('/', methods=['GET'])
def show_foundation():
    """Show the foundation form"""
    return render_template('foundation.html')

@bp.route('/foundation', methods=['POST'])
def create_foundation():
    """Create new test run and persona from foundation data"""
    try:
        foundation_data = request.get_json()
        current_app.logger.info(f"Received foundation data: {foundation_data}")
        
        # Create persona and test run
        persona_id, test_run_id = current_app.db.create_persona_from_foundation(
            foundation_data['foundation']
        )
        current_app.logger.info(f"Created persona {persona_id} with test run {test_run_id}")
        
        # Generate stories using pipeline_utils
        story = run_story_generation(persona_id, test_run_id)
        story_result = {
            "status": "success" if not story.startswith("Error:") else "error",
            "data": {"story": story} if not story.startswith("Error:") else {"error": story[7:]}
        }
        
        if story_result["status"] == "error":
            raise Exception(story_result["data"]["error"])
            
        # Set initial clarity score
        current_app.db.set_foundation_clarity(test_run_id)
        
        # Get available prompts
        prompts = current_app.db.get_available_prompts()
        
        return jsonify({
            "status": "success",
            "data": {
                "test_run_id": test_run_id,
                "persona_id": persona_id,
                "available_prompts": prompts,
                "story_generation": story_result["data"]
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": {
                "code": "FOUNDATION_ERROR",
                "message": str(e)
            }
        }), 400 