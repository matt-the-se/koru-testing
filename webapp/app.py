import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # Adds parent directory to path

from flask import Flask
from webapp.routes import foundation, prompts, responses, themes, stories, pages, pipeline
from shared.database.manager import DatabaseManager, DBEnvironment
from config import FLASK_CONFIG, webapp_logger

def create_app():
    app = Flask(__name__, 
                template_folder='templates',  # Explicitly set template folder
                static_folder='static')       # Explicitly set static folder
    
    app.logger.info(f"Template folder: {app.template_folder}")
    app.logger.info(f"Static folder: {app.static_folder}")
    
    # Load config from global config
    app.config.update(FLASK_CONFIG)
    
    # Initialize database manager
    app.db = DatabaseManager(DBEnvironment.WEBAPP)
    app.logger = webapp_logger
    
    # Register blueprints
    app.register_blueprint(pages.bp)
    app.register_blueprint(foundation.bp)
    app.register_blueprint(prompts.bp)
    app.register_blueprint(responses.bp)
    app.register_blueprint(themes.bp)
    app.register_blueprint(stories.bp)
    app.register_blueprint(pipeline.bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=app.config['DEBUG']
    ) 