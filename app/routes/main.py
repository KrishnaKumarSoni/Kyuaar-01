"""Main routes for the application."""
from flask import render_template
from app.routes import main_bp

@main_bp.route('/')
def index():
    """Landing page."""
    return {'message': 'Welcome to Kyuaar API', 'status': 'active'}

@main_bp.route('/health')
def health():
    """Health check endpoint."""
    return {'status': 'healthy', 'service': 'kyuaar-api'}