from flask import Blueprint, jsonify, request, current_app

bp = Blueprint('responses', __name__, url_prefix='/api/v1')

@bp.route('/responses', methods=['POST'])
def submit_response():
    data = request.get_json()
    # Add logging to see what we're receiving
    current_app.logger.info(f"[responses] Received data: {data}")
    try:
        test_run_id = data.get('test_run_id')
        prompt_id = data.get('prompt_id')
        persona_id = data.get('persona_id')
        response_text = data.get('response_text')
        current_app.db.store_prompt_response(
            test_run_id=test_run_id,
            prompt_id=prompt_id,
            persona_id=persona_id,
            response_text=response_text
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"[responses] Error storing response: {e}")
        return jsonify({'error': str(e)}), 500

@bp.route('/responses/<test_run_id>', methods=['GET'])
def get_responses():
    return jsonify({"status": "success", "data": {"responses": []}})

@bp.route('/', methods=['POST'])
def save_response():
    """Save a single response"""
    try:
        data = request.get_json()
        test_run_id = data.get('test_run_id')
        prompt_id = data.get('prompt_id')
        variation_id = data.get('variation_id')
        response_text = data.get('response_text')

        current_app.logger.info(f"[responses] Received data: {data}")
        current_app.logger.info(f"[responses] Saving response: test_run_id={test_run_id}, prompt_id={prompt_id}, variation_id={variation_id}")
        
        current_app.db.store_prompt_response(
            test_run_id=test_run_id,
            prompt_id=prompt_id,
            variation_id=variation_id,
            response_text=response_text
        )

        return jsonify({'status': 'success'})
    except Exception as e:
        current_app.logger.error(f"Error saving response: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 