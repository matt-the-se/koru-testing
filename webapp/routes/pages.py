from flask import Blueprint, render_template, current_app, redirect, url_for, request

bp = Blueprint('pages', __name__)  # No URL prefix for pages

@bp.route('/')
def index():
    """Landing page - redirects to foundation for now"""
    current_app.logger.info('Attempting to render foundation.html')
    try:
        return render_template('foundation.html')
    except Exception as e:
        current_app.logger.error(f'Error rendering template: {e}')
        raise

@bp.route('/foundation')
def foundation():
    """Foundation page"""
    return render_template('foundation.html')

@bp.route('/core-vision')
def core_vision():
    """Core Vision page"""
    try:
        # Get IDs from query parameters
        persona_id = request.args.get('persona_id')
        test_run_id = request.args.get('test_run_id')
        
        if not persona_id or not test_run_id:
            current_app.logger.warning("Missing persona_id or test_run_id")
            return redirect(url_for('pages.foundation'))

        current_app.logger.info(f"Core Vision page requested with persona_id={persona_id}, test_run_id={test_run_id}")

        # Get foundation data
        foundation = current_app.db.get_persona_foundation(persona_id)
        current_app.logger.info(f"Got foundation data: {foundation}")

        # Get core vision prompts
        prompts = current_app.db.get_available_prompts(section='Core Vision')
        current_app.logger.info(f"Raw prompts data: {prompts}")

        # Get clarity score
        clarity = current_app.db.get_clarity_scores(test_run_id)
        current_app.logger.info(f"Raw clarity data: {clarity}")
        
        # Get the persona's clarity scores
        persona_scores = clarity.get(str(persona_id), {})
        total_clarity = persona_scores.get('total_clarity_score', 0)
        current_app.logger.info(f"Total clarity: {total_clarity}")
        
        # Cap at 100% and convert to integer percentage
        clarity_score = min(int(total_clarity * 100), 100) if total_clarity else 10
        current_app.logger.info(f"Final clarity score: {clarity_score}")

        current_app.logger.info(f"Rendering template with: prompts={len(prompts)}, clarity={clarity_score}, foundation={foundation}")

        return render_template('core_vision.html',
                             foundation=foundation,
                             prompts=prompts,
                             clarity_score=clarity_score)
    except Exception as e:
        current_app.logger.error(f'Error loading core vision page: {e}', exc_info=True)
        return redirect(url_for('pages.foundation')) 

@bp.route('/actualization')
def actualization():
    """Actualization page"""
    try:
        # Get IDs from query parameters
        persona_id = request.args.get('persona_id')
        test_run_id = request.args.get('test_run_id')
        
        current_app.logger.info(f"Actualization page requested with persona_id={persona_id}, test_run_id={test_run_id}")

        if not persona_id or not test_run_id:
            current_app.logger.warning('Missing persona_id or test_run_id')
            return redirect(url_for('pages.foundation'))

        # Get foundation data
        foundation = current_app.db.get_persona_foundation(persona_id)
        
        # Get actualization prompts
        prompts = current_app.db.get_available_prompts(section='Actualization')
        
        # Get clarity score
        clarity = current_app.db.get_clarity_scores(test_run_id)
        # Get the first persona's total clarity score
        first_persona_scores = list(clarity.values())[0] if clarity else {}
        total_clarity = first_persona_scores.get('total_clarity_score', 0)
        # Cap at 100% and convert to integer percentage
        clarity_score = min(int(total_clarity * 100), 100)
        
        # Get saved responses for this section
        saved_responses = current_app.db.get_saved_responses(test_run_id, 'Actualization')
        
        return render_template('actualization.html',
                             foundation=foundation,
                             prompts=prompts,
                             saved_responses=saved_responses,
                             clarity_score=clarity_score)
    except Exception as e:
        current_app.logger.error(f'Error loading actualization page: {e}', exc_info=True)
        return redirect(url_for('pages.foundation')) 

@bp.route('/stories')
def stories():
    """Stories page"""
    try:
        persona_id = request.args.get('persona_id')
        test_run_id = request.args.get('test_run_id')
        
        current_app.logger.info(f"Stories page requested with params: persona_id={persona_id}, test_run_id={test_run_id}")
        
        if not persona_id or not test_run_id:
            current_app.logger.warning(f"Missing required parameters: persona_id={persona_id}, test_run_id={test_run_id}")
            return redirect(url_for('pages.foundation'))
            
        # Get foundation data
        foundation = current_app.db.get_persona_foundation(persona_id)
        
        # Get clarity score
        clarity = current_app.db.get_clarity_scores(test_run_id)
        # Get the first persona's total clarity score
        first_persona_scores = list(clarity.values())[0] if clarity else {}
        total_clarity = first_persona_scores.get('total_clarity_score', 0)
        # Cap at 100% and convert to integer percentage
        clarity_score = min(int(total_clarity * 100), 100)
        
        return render_template('stories.html',
                             foundation=foundation,
                             clarity_score=clarity_score)
    except Exception as e:
        current_app.logger.error(f'Error loading stories page: {e}', exc_info=True)
        return redirect(url_for('pages.foundation')) 