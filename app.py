"""
app.py — Main Flask application entry point.

Handles routing and error handling only. Business logic lives in
page_handlers.py. File handling lives in file_processors.py.

Adding a new page:
  1. Create app/templates/my_tool.html extending base.html
  2. Add handler logic to app/page_handlers.py if needed
  3. No changes to this file required — generic routing picks it up automatically
     URL: /my-tool  →  template: my_tool.html

Custom route registration:
  If app/page_handlers.py defines register_routes(app, claude_client_ref),
  it will be called automatically after initialisation. Use this to add
  app-specific API endpoints (e.g. /api/profiles, /api/myapp/run).

Page types (set via hidden field name="page_type" in the form):
  claude-call  — sends form data to Claude API (default)
  no-call      — processes form data server-side, no Claude
  custom       — dispatches to handle_custom_page() in page_handlers.py
"""

from flask import render_template, request, jsonify
from datetime import datetime
import os
import re
import json

from config import (
    create_app, setup_logging, setup_rate_limiter,
    setup_claude_client, ensure_directories
)
from file_processors import process_uploaded_file, validate_file, load_server_files
from page_handlers import handle_no_call_page, handle_claude_call_page
from utils import get_session_id, get_server_files_info

# ── Initialise ────────────────────────────────────────────────────────────────
app = create_app()
logger = setup_logging()
limiter = setup_rate_limiter(app)
claude_client = setup_claude_client()
ensure_directories()

if claude_client:
    logger.info("Application started — Claude API available")
else:
    logger.warning("Application started — Claude API unavailable (CLAUDE_API_KEY not set)")

# ── Optional custom route registration ───────────────────────────────────────
# If page_handlers.py defines register_routes(app, claude_client_ref), call it.
# This is the standard way for apps to add their own API endpoints.
try:
    from page_handlers import register_routes
    register_routes(app, lambda: claude_client)
    logger.info("Custom routes registered from page_handlers.register_routes()")
except (ImportError, AttributeError):
    pass  # App doesn't define custom routes — that's fine

# ── Optional custom page handler ─────────────────────────────────────────────
# Imported here so the generic_api route can call it without a nested import.
try:
    from page_handlers import handle_custom_page as _handle_custom_page
except (ImportError, AttributeError):
    _handle_custom_page = None


# ── Standard routes ───────────────────────────────────────────────────────────

@app.route('/')
def home():
    get_session_id()
    return render_template('home.html', available_pages=_get_available_pages())


@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'claude_available': claude_client is not None,
        'app_name': app.config.get('APP_NAME', 'Flask App')
    })


@app.route('/favicon.ico')
def favicon():
    return '', 204


# ── Generic page route ────────────────────────────────────────────────────────

@app.route('/<page_name>')
def generic_page(page_name):
    """
    Serve any page that has a corresponding template.
    URL /my-tool → templates/my_tool.html

    A page can declare additional server_files directories by including a
    script tag with id="server_dirs_config" containing JSON:
        {"directories": ["shared", "my_tool"]}
    """
    get_session_id()
    logger.info(f"Page: {page_name}")

    template_name = page_name.replace('-', '_') + '.html'
    directories_to_load = _get_template_directories(page_name, template_name)

    try:
        server_files_info = get_server_files_info(page_name, directories_to_load)
    except Exception as e:
        logger.error(f"Error loading server files info for {page_name}: {e}")
        server_files_info = []

    try:
        return render_template(
            template_name,
            page_name=page_name,
            server_files_info=server_files_info,
            available_pages=_get_available_pages()
        )
    except Exception as e:
        logger.error(f"Template error for {template_name}: {e}")
        return render_template('404.html'), 404


# ── Generic API route ─────────────────────────────────────────────────────────

@app.route('/api/<page_name>', methods=['POST'])
@limiter.limit("30 per minute")
def generic_api(page_name):
    """
    Generic API endpoint for all pages.
    Dispatches based on the page_type hidden field in the submitted form:
      claude-call  — calls Claude API (default)
      no-call      — server-side processing only
      custom       — calls handle_custom_page() from page_handlers.py
    """
    try:
        uploaded_files_data = {}
        for field_name in request.files:
            file = request.files[field_name]
            if file and file.filename:
                is_valid, message = validate_file(file)
                if not is_valid:
                    return jsonify({'error': f'{field_name}: {message}'}), 400
                try:
                    file_data = process_uploaded_file(file)
                    if file_data:
                        clean_key = field_name.replace('_file', '').replace('_', ' ')
                        uploaded_files_data[clean_key] = file_data
                        logger.info(f"Processed upload: {file.filename} → {clean_key}")
                except Exception as e:
                    return jsonify({'error': f'Error processing {field_name}: {str(e)}'}), 400

        template_name = page_name.replace('-', '_') + '.html'
        directories_to_load = _get_template_directories(page_name, template_name)
        server_files_data = load_server_files(page_name, directories_to_load)

        form_data = request.form.to_dict()
        session_id = get_session_id()
        page_type = form_data.get('page_type', 'claude-call')

        logger.info(f"API: {page_name} [{page_type}] — session: {session_id}")

        if page_type == 'no-call':
            return handle_no_call_page(
                page_name, form_data, uploaded_files_data,
                server_files_data, session_id
            )
        elif page_type == 'claude-call':
            return handle_claude_call_page(
                page_name, form_data, uploaded_files_data,
                server_files_data, session_id, claude_client
            )
        elif page_type == 'custom':
            if _handle_custom_page is None:
                return jsonify({'error': 'page_type=custom but handle_custom_page() not defined in page_handlers.py'}), 501
            return _handle_custom_page(
                page_name, form_data, uploaded_files_data,
                server_files_data, session_id, claude_client
            )
        else:
            return jsonify({'error': f'Unknown page_type: {page_type}'}), 400

    except Exception as e:
        logger.error(f"API error for {page_name}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ── Binary file serving ───────────────────────────────────────────────────────

@app.route('/api/<page_name>/file/<filename>', methods=['GET'])
def serve_page_file(page_name, filename):
    from binary_file_handler import serve_binary_file
    logger.info(f"Binary file request: {page_name}/{filename}")
    return serve_binary_file(page_name, filename)


@app.route('/api/<page_name>/files', methods=['GET'])
def list_page_files(page_name):
    from binary_file_handler import list_binary_files
    extensions = request.args.getlist('ext')
    files = list_binary_files(page_name, extensions if extensions else None)
    return jsonify({'files': files})


# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 10MB.'}), 413


@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_available_pages():
    """Return list of {name, url} dicts for all discovered page templates."""
    pages = []
    template_dir = app.template_folder
    skip = {'base.html', 'home.html', '404.html', '500.html'}
    try:
        for filename in sorted(os.listdir(template_dir)):
            if filename.endswith('.html') and filename not in skip:
                page_name = filename[:-5]  # strip .html
                url_name  = page_name.replace('_', '-')
                display   = page_name.replace('_', ' ').title()
                pages.append({'name': display, 'url': f'/{url_name}'})
    except Exception as e:
        logger.error(f"Error discovering pages: {e}")
    return pages


def _get_template_directories(page_name, template_name):
    """
    Return list of server_files subdirectories to load for a page.
    Always includes the page's own directory first.
    Extends the list if the template declares a server_dirs_config script tag.
    """
    directories = [page_name]
    try:
        template_path = os.path.join(app.template_folder, template_name)
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                content = f.read()
            match = re.search(
                r'<script[^>]*id="server_dirs_config"[^>]*>(.*?)</script>',
                content, re.DOTALL
            )
            if match:
                config = json.loads(match.group(1).strip())
                for d in config.get('directories', []):
                    if d not in directories:
                        directories.append(d)
                logger.info(f"Directories for {page_name}: {directories}")
    except Exception as e:
        logger.warning(f"Could not parse server_dirs_config for {page_name}: {e}")
    return directories


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    )
