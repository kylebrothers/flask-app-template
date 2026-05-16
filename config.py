"""
config.py — Flask app factory and shared service setup.
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
    need Claude to function normally.
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
        logging.getLogger(__name__).error(f"Failed to initialise Claude client: {e}")
        return None


def ensure_directories():
    """
    Create required runtime directories if they don't exist.

    Standard directories (logs, server_files, static) are always created.
    If DB_PATH is set in the environment, its parent directory is also created
    so apps using SQLite don't need their own os.makedirs call.
    """
    for directory in ['logs', 'server_files', 'static']:
        os.makedirs(directory, exist_ok=True)

    db_path = os.environ.get('DB_PATH')
    if db_path:
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)


# ── Optional app-specific config extension ───────────────────────────────────
# Create app/config_extra.py to extend config without overriding this file.
try:
    import config_extra  # noqa: F401
except ImportError:
    pass
