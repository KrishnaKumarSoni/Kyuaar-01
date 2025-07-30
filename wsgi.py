"""WSGI configuration for Vercel deployment."""
import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

# Create Flask application instance
app = create_app()

# WSGI application object for Gunicorn
application = app

if __name__ == "__main__":
    app.run(debug=False)