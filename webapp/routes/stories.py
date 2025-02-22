from flask import Blueprint, jsonify, request, current_app, send_file, render_template
import subprocess
import os
from TTS.api import TTS
import io

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

        script_path = os.path.join(current_app.root_path, '..', 'generate_stories', 'generate_stories.py')
        
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
        return jsonify(story_data)
    except Exception as e:
        current_app.logger.error(f"Error fetching story: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/story/can-generate/<test_run_id>', methods=['GET'])
def can_generate_story(test_run_id):
    try:
        # Get current story content
        story_data = current_app.db.get_story_content(test_run_id)
        last_input_change = current_app.db.get_last_input_change(test_run_id)
        
        # Show generate button if:
        # 1. No story exists (status is pending)
        # 2. Story exists but is empty (content is None)
        # 3. Story exists but inputs have changed since generation
        can_generate = (
            story_data['status'] == 'pending' or
            story_data['content'] is None or
            (last_input_change and story_data.get('generated_at') and last_input_change > story_data['generated_at'])
        )
        
        return jsonify({"can_generate": can_generate})
    except Exception as e:
        current_app.logger.error(f"Error checking story generation: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route('/tts/<int:test_run_id>', methods=['GET'])
def text_to_speech(test_run_id):
    try:
        # Get story content
        story = current_app.db.get_story_content(test_run_id)
        current_app.logger.info(f"Retrieved story for TTS: {story}")
        if not story or story['status'] != 'complete':
            return jsonify({"error": "Story not found"}), 404

        # Initialize TTS with a pleasant female voice
        # Try different models:
        # tts = TTS(model_name="tts_models/en/jenny/jenny")  # More natural female voice
        # tts = TTS(model_name="tts_models/en/vctk/vits")    # Multi-speaker model
        
        # Using VITS model with adjustable settings
        tts = TTS(model_name="tts_models/en/vctk/vits", progress_bar=False)
        current_app.logger.info("TTS model initialized")
        
        # Generate audio
        wav = tts.tts(
            text=story['content'],
            speaker="p335",  # Female voice from VCTK
            speed=0.95,      # Slightly slower for clarity (0.5-2.0)
            emotion="Happy"  # Some models support emotion
        )
        current_app.logger.info("Audio generated")
        
        # Convert to bytes
        wav_io = io.BytesIO()
        tts.synthesizer.save_wav(wav, wav_io)
        wav_io.seek(0)
        
        return send_file(
            wav_io,
            mimetype='audio/wav',
            as_attachment=False,
            download_name='story.wav'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating TTS: {e}")
        return jsonify({"error": str(e)}), 500

@bp.route('/stories', methods=['GET'])
def stories_page():
    test_run_id = request.args.get('test_run_id')
    story_data = current_app.db.get_story_content(test_run_id) if test_run_id else None
    story_content = story_data.get('content') if story_data and story_data['status'] == 'complete' else None
    
    # Get clarity score properly
    try:
        clarity_data = current_app.db.get_clarity_scores(test_run_id)
        clarity_score = clarity_data.get('overall', 0) if clarity_data else 0
    except Exception as e:
        current_app.logger.error(f"Error getting clarity score: {e}")
        clarity_score = 0
    
    return render_template(
        'stories.html',
        story_content=story_content,
        clarity_score=clarity_score
    )

@bp.route('/story/clear/<test_run_id>', methods=['POST'])
def clear_story(test_run_id):
    """Clear story content when inputs change"""
    try:
        current_app.db.clear_story(test_run_id)
        return jsonify({"status": "success"})
    except Exception as e:
        current_app.logger.error(f"Error clearing story: {e}")
        return jsonify({"error": str(e)}), 500 