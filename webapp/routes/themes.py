from flask import Blueprint, jsonify

bp = Blueprint('themes', __name__, url_prefix='/api/v1')

@bp.route('/themes/<test_run_id>', methods=['GET'])
def get_theme_analysis():
    return jsonify({"status": "success", "data": {"themes": {}}})

@bp.route('/themes/<test_run_id>/progress', methods=['GET'])
def get_theme_progress():
    return jsonify({"status": "success", "data": {"sections": {}}}) 