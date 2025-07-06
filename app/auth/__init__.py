from flask import Blueprint

bp = Blueprint('auth', __name__)

# Import routes after the Blueprint is created to avoid circular imports
from app.auth import routes