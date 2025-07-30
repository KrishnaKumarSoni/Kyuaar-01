"""
Configuration and settings routes
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
import logging

config_bp = Blueprint('config', __name__)
logger = logging.getLogger(__name__)

@config_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('config/settings.html')