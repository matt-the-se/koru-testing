from flask import Blueprint, jsonify, request, current_app, render_template
from ..pipeline_utils import calculate_clarity  # Only need clarity calculation

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
            foundation_data["foundation"]
        )
        current_app.logger.info(f"Created persona {persona_id} with test run {test_run_id}")
        
        # Initialize clarity scores with empty structure
        clarity_scores = {
            "overall": 0.0,
            "sections": {
                "freeform": 0.0,
                "core_vision": 0.0,
                "actualization": 0.0
            },
            "themes": {},
            "foundation_complete": True
        }
        current_app.db.set_foundation_clarity(test_run_id, clarity_scores)
        
        return jsonify({
            "status": "success", 
            "data": {
                "test_run_id": test_run_id,
                "persona_id": persona_id
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