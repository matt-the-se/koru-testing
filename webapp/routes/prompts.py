from flask import Blueprint, jsonify, current_app, request

bp = Blueprint('prompts', __name__, url_prefix='/api/v1')

@bp.route('/prompts', methods=['GET'])
def get_prompts():
    """Get prompts, optionally filtered by section"""
    try:
        # Get section from query params, default to core_vision
        section = request.args.get('section', 'core_vision')
        
        # Get prompts from database
        prompts = current_app.db.get_available_prompts(section=section)
        
        current_app.logger.info(f"Retrieved {len(prompts)} prompts for section: {section}")
        
        return jsonify({
            "status": "success",
            "data": {
                "prompts": prompts
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error getting prompts: {e}")
        return jsonify({
            "status": "error",
            "error": {
                "code": "PROMPT_ERROR",
                "message": str(e)
            }
        }), 500 