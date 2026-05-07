"""
utils.py — Shared utility functions.

This file is part of flask-app-template. Add app-specific utilities to
app/utils_extra.py rather than modifying this file.
"""

import os
import uuid
import logging
from flask import session

logger = logging.getLogger(__name__)

# ── Session ───────────────────────────────────────────────────────────────────

def get_session_id():
    """Return the current session ID, creating one if it doesn't exist."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']


# ── Server files ──────────────────────────────────────────────────────────────

# File types recognised for display purposes
_FILE_TYPE_MAP = {
    '.docx': 'Word Document',
    '.doc':  'Word Document (Legacy)',
    '.pdf':  'PDF Document',
    '.txt':  'Text File',
    '.xlsx': 'Excel Spreadsheet',
    '.csv':  'CSV File',
    '.json': 'JSON File',
}

_SUPPORTED_EXTENSIONS = {'.docx', '.pdf', '.txt'}


def get_server_files_info(page_name, directories=None):
    """
    Return metadata about files in the server_files NAS volume for display
    in page templates (e.g. populating a <select> element).

    Args:
        page_name:    Name of the current page (used as default directory).
        directories:  List of subdirectories under server_files/ to scan.
                      Defaults to [page_name].

    Returns:
        List of dicts with keys: filename, display_name, file_type,
        size, supported, source_directory.
    """
    if directories is None:
        directories = [page_name]

    multi = len(directories) > 1
    results = []

    for directory in directories:
        server_dir = f"/app/server_files/{directory}"
        if not os.path.exists(server_dir):
            logger.debug(f"server_files directory not found: {server_dir}")
            continue

        try:
            for filename in os.listdir(server_dir):
                file_path = os.path.join(server_dir, filename)
                if not os.path.isfile(file_path):
                    continue

                ext = os.path.splitext(filename)[1].lower()
                size_str = _format_file_size(os.path.getsize(file_path))
                base_name = clean_filename(filename)

                # Prefix display name with directory when scanning multiple dirs
                # and the file doesn't come from the page's own directory
                if multi and directory != page_name:
                    display_name = f"{directory.replace('_', ' ').title()} — {base_name}"
                else:
                    display_name = base_name

                results.append({
                    'filename':         filename,
                    'display_name':     display_name,
                    'file_type':        _FILE_TYPE_MAP.get(ext, 'Unknown'),
                    'size':             size_str,
                    'supported':        ext in _SUPPORTED_EXTENSIONS,
                    'source_directory': directory,
                })

        except Exception as e:
            logger.error(f"Error scanning server_files/{directory}: {e}")
            continue

    results.sort(key=lambda x: x['display_name'])
    logger.info(
        f"server_files info: {len(results)} files from "
        f"{len(directories)} director{'y' if len(directories) == 1 else 'ies'}"
    )
    return results


# ── Text helpers ──────────────────────────────────────────────────────────────

def truncate_text(text, max_length=500):
    """Truncate text to max_length characters, appending ellipsis if cut."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + '…'


def clean_filename(filename):
    """Convert a filename (without extension) to a human-readable title."""
    return os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()


def sanitize_form_key(key):
    """Convert a form field name to a human-readable label."""
    return key.replace('_', ' ').title()


def count_form_fields(form_data, exclude_keys=None):
    """Count non-empty form fields, ignoring system/internal keys."""
    if exclude_keys is None:
        exclude_keys = {'page_type', 'page_title', 'claude_prompt'}
    return sum(
        1 for k, v in form_data.items()
        if k not in exclude_keys and str(v).strip()
    )


# ── File size formatting ──────────────────────────────────────────────────────

def _format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


# Keep public alias for any templates or handlers that call it directly
format_file_size = _format_file_size
