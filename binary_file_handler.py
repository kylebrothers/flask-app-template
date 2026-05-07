"""
binary_file_handler.py — Serve binary files from the server_files NAS volume.

Used by the /api/<page_name>/file/<filename> route in app.py to allow
templates to download or display files stored on the NAS (e.g. Word
templates, PDFs, images) directly in the browser.

This file is part of flask-app-template and rarely needs to be overridden.
"""

import os
import logging
from flask import send_file, abort
from urllib.parse import unquote
from werkzeug.utils import safe_join

logger = logging.getLogger(__name__)

_BASE_PATH = "/app/server_files"

_MIME_TYPES = {
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.doc':  'application/msword',
    '.pdf':  'application/pdf',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xls':  'application/vnd.ms-excel',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.ppt':  'application/vnd.ms-powerpoint',
    '.txt':  'text/plain',
    '.csv':  'text/csv',
    '.json': 'application/json',
    '.png':  'image/png',
    '.jpg':  'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.gif':  'image/gif',
    '.webp': 'image/webp',
}


def serve_binary_file(page_name, filename):
    """
    Serve a file from /app/server_files/<page_name>/<filename>.

    Files are served inline (displayed in browser) where possible.
    Path traversal is prevented via werkzeug's safe_join.
    """
    try:
        filename = unquote(filename)
        file_path = safe_join(_BASE_PATH, page_name, filename)

        if not file_path or not file_path.startswith(_BASE_PATH):
            logger.warning(f"Blocked path traversal attempt: {page_name}/{filename}")
            abort(403)

        if not os.path.isfile(file_path):
            logger.warning(f"Binary file not found: {file_path}")
            abort(404)

        ext = os.path.splitext(filename)[1].lower()
        mime_type = _MIME_TYPES.get(ext, 'application/octet-stream')

        logger.info(f"Serving: {file_path} [{mime_type}]")
        return send_file(
            file_path,
            mimetype=mime_type,
            as_attachment=False,
            download_name=filename
        )

    except Exception as e:
        logger.error(f"Error serving {page_name}/{filename}: {e}")
        abort(500)


def list_binary_files(page_name, extensions=None):
    """
    List files available in server_files/<page_name>, optionally filtered
    by extension.

    Args:
        page_name:   Page directory name.
        extensions:  List of extensions to include, e.g. ['.docx', '.pdf'].
                     If None, all files are returned.

    Returns:
        List of dicts: { filename, size, url }
    """
    server_dir = os.path.join(_BASE_PATH, page_name)
    if not os.path.exists(server_dir):
        return []

    results = []
    try:
        for filename in sorted(os.listdir(server_dir)):
            file_path = os.path.join(server_dir, filename)
            if not os.path.isfile(file_path):
                continue
            if extensions:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in extensions:
                    continue
            results.append({
                'filename': filename,
                'size': os.path.getsize(file_path),
                'url': f'/api/{page_name}/file/{filename}',
            })
    except Exception as e:
        logger.error(f"Error listing server_files/{page_name}: {e}")

    return results
