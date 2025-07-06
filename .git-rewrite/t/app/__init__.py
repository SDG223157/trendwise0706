from flask import Flask
from flask.cli import load_dotenv
import os

def create_app():
    app = Flask(__name__)
    
    # Load environment variables
    load_dotenv()
    
    # Config
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
    
    # Register routes
    from app import routes
    app.register_blueprint(routes.bp)
    
    return app
