from flask import Blueprint, jsonify, request, current_app
import subprocess
import os

bp = Blueprint('stories', __name__, url_prefix='/api/v1')

@bp.route('/stories', methods=['POST'])
def generate_story():
    try:
        data = request.get_json()
        test_run_id = data.get('test_run_id')
        
        if not test_run_id:
            return jsonify({
                "status": "error",
                "message": "Missing test_run_id"
            }), 400

        script_path = os.path.join(current_app.root_path, '..', 'generate-stories', 'generate_stories.py')
        
        # Add project root to PYTHONPATH
        env = os.environ.copy()
        env['PYTHONPATH'] = os.path.join(current_app.root_path, '..')
        
        result = subprocess.run(
            ['python', script_path, str(test_run_id)],
            capture_output=True,
            text=True,
            env=env
        )

        if result.returncode != 0:
            current_app.logger.error(f"Script error: {result.stderr}")
            return jsonify({
                "status": "error",
                "message": "Error generating story"
            }), 500

        return jsonify({
            "status": "success",
            "message": "Story generation started"
        })

    except Exception as e:
        current_app.logger.error(f"Error generating story: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e)
        }), 500

@bp.route('/story/<test_run_id>', methods=['GET'])
def get_story(test_run_id):
    try:
        story_data = current_app.db.get_story_content(test_run_id)
        
        # Only return error if we actually don't have content
        if story_data["status"] == "error":
            return jsonify({
                "status": "error",
                "message": "Error fetching story"
            }), 500
            
        # Return the story data, even if pending
        return jsonify(story_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching story: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500 