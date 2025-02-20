from flask import Blueprint, jsonify, current_app, request
from webapp.pipeline_utils import (
    run_input_processor,
    run_keyword_matcher,
    run_input_classifier,
    calculate_clarity
)

bp = Blueprint('pipeline', __name__, url_prefix='/api/v1/pipeline')

@bp.route('/run', methods=['POST'])
def run_pipeline():
    """Run the full analysis pipeline on a test run's inputs"""
    try:
        data = request.get_json()
        test_run_id = data.get('test_run_id')
        persona_id = data.get('persona_id')

        current_app.logger.info(f"Pipeline received request with: test_run_id={test_run_id}, persona_id={persona_id}")

        if not test_run_id or not persona_id:
            current_app.logger.error("Missing test_run_id or persona_id")
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'MISSING_PARAMS',
                    'message': 'Missing test_run_id or persona_id'
                }
            }), 400

        current_app.logger.info(f"Starting pipeline for test_run_id={test_run_id}")

        try:
            # Run each stage with detailed logging
            current_app.logger.info("Starting input processing...")
            run_input_processor(current_app.logger, test_run_id)
            
            current_app.logger.info("Starting keyword matching...")
            run_keyword_matcher(test_run_id)
            
            current_app.logger.info("Starting input classification...")
            run_input_classifier(test_run_id)
            
            current_app.logger.info("Calculating clarity score...")
            clarity_score = calculate_clarity(test_run_id)
            
            current_app.logger.info(f"Pipeline complete. Clarity score: {clarity_score}")

        except Exception as e:
            current_app.logger.error(f"Pipeline stage error: {str(e)}", exc_info=True)
            raise

        # Save clarity score
        current_app.db.update_clarity_scores(test_run_id, clarity_score)

        return jsonify({
            'status': 'success',
            'data': {
                'clarity_score': clarity_score
            }
        })

    except Exception as e:
        current_app.logger.error(f"Pipeline error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': {
                'code': 'PIPELINE_ERROR',
                'message': str(e)
            }
        }), 500 