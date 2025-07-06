# app/news/__init__.py
from flask import Blueprint

bp = Blueprint('news', __name__, url_prefix='/news')

from app.news import routes  # Import routes after creating blueprint