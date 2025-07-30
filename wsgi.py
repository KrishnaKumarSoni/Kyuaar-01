"""
WSGI entry point for Vercel deployment
Configures the Flask application for serverless deployment
"""

import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import app

# This is the entry point for WSGI servers like Gunicorn and Vercel
application = app

if __name__ == "__main__":
    application.run(debug=False)