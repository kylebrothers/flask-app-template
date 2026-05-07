"""
config.py — Flask app factory and shared service setup.

This file is part of flask-app-template and is pulled into app images at
build time. Do not modify here for app-specific needs — override in app/
if necessary, or extend via app/config_extra.py (imported at bottom of this
file if present).
"""

import os
import logging
import anthropic
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY', 'dev-secret-key-change-in-production'
    )
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB upload limit
    app.config['APP_NAME'] = os.environ.get('APP_NAME', 'Flask App')

    return app


def setup_logging():
    """Configure application logging to file and stdout."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def setup_rate_limiter(app):
    """
    Configure rate limiting.

    Memory-backed — no Redis required. Suitable for single-user home network
    deployments. Limits reset if the container restarts.
    """
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per hour"],
        storage_uri="memory://"
    )
    return limiter


def setup_claude_client():
    """
    Initialize the Anthropic Claude API client.

    Returns None if CLAUDE_API_KEY is not set, allowing pages that don't
    need Claude to function normally. Pages that require Claude should check
    for None and return an appropriate error.
    """
    api_key = os.environ.get('CLAUDE_API_KEY')
    if not api_key:
        logging.getLogger(__name__).warning(
            "CLAUDE_API_KEY not set — Claude API unavailable"
        )
        return None
    try:
        return anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        logging.getLogger(__name__).error(
            f"Failed to initialize Claude client: {e}"
        )
        return None


def ensure_directories():
    """
    Create required runtime directories if they don't exist.

    These are created inside the container. Persistent data (logs,
    server_files, database) should be on NAS volumes mounted over these paths.
    """
    for directory in ['logs', 'server_files', 'static']:
        os.makedirs(directory, exist_ok=True)


# ── Optional app-specific config extension ─────────────────────────────────
# If an app needs to extend config without overriding this file entirely,
# create app/config_extra.py. It will be imported here if present.
try:
    import config_extra  # noqa: F401
except ImportError:
    pass
