"""
file_processors.py — File upload handling and server-file loading.

Supports .docx, .pdf, and .txt out of the box. DOCX and PDF processing
require python-docx and PyPDF2 respectively — add these to app/requirements.txt
if your app handles those file types. If the packages are not installed,
those file types are gracefully skipped with a warning.

This file is part of flask-app-template. For app-specific file types or
processing logic, override this file in app/file_processors.py.
"""

import os
import io
import logging
import zipfile

logger = logging.getLogger(__name__)

# ── Optional dependency detection ─────────────────────────────────────────────

try:
    from docx import Document as _DocxDocument
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False
    logger.info("python-docx not installed — DOCX processing unavailable. "
                "Add 'python-docx' to app/requirements.txt to enable.")

try:
    import PyPDF2 as _PyPDF2
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False
    logger.info("PyPDF2 not installed — PDF processing unavailable. "
                "Add 'PyPDF2' to app/requirements.txt to enable.")


# ── DOCX extraction ───────────────────────────────────────────────────────────

def extract_text_from_docx(file_stream):
    """Extract plain text from a Word document stream."""
    if not _DOCX_AVAILABLE:
        raise RuntimeError("python-docx is not installed")
    try:
        doc = _DocxDocument(file_stream)
        lines = []
        for para in doc.paragraphs:
            if para.text.strip():
                lines.append(para.text.strip())
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    lines.append(' | '.join(cells))
        return '\n'.join(lines)
    except Exception as e:
        logger.error(f"DOCX text extraction error: {e}")
        raise ValueError(f"Failed to extract text from Word document: {e}")


def extract_xml_from_docx(file_stream):
    """
    Extract raw XML parts from a Word document (docx is a zip archive).
    Returns a dict of part name → XML string. Useful for template-based
    document generation workflows.
    """
    try:
        file_stream.seek(0)
        xml_data = {}
        with zipfile.ZipFile(file_stream, 'r') as z:
            for part in ('word/document.xml', 'word/styles.xml',
                         'docProps/core.xml', 'docProps/app.xml'):
                if part in z.namelist():
                    xml_data[part.split('/')[-1].replace('.xml', '')] = \
                        z.read(part).decode('utf-8')
            xml_data['file_list'] = z.namelist()
        return xml_data
    except Exception as e:
        logger.error(f"DOCX XML extraction error: {e}")
        return {"error": str(e)}


# ── PDF extraction ────────────────────────────────────────────────────────────

def extract_text_from_pdf(file_stream):
    """Extract plain text from a PDF stream, page by page."""
    if not _PDF_AVAILABLE:
        raise RuntimeError("PyPDF2 is not installed")
    try:
        reader = _PyPDF2.PdfReader(file_stream)
        pages = []
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text and text.strip():
                    pages.append(f"--- Page {i + 1} ---\n{text.strip()}")
            except Exception as e:
                logger.warning(f"Could not extract text from PDF page {i + 1}: {e}")
        if not pages:
            raise ValueError("No text could be extracted from this PDF")
        return '\n'.join(pages)
    except Exception as e:
        logger.error(f"PDF text extraction error: {e}")
        raise ValueError(f"Failed to extract text from PDF: {e}")


def extract_form_data_from_pdf(file_stream):
    """
    Extract form field values and per-page metadata from a PDF.
    Returns a dict. Falls back gracefully if the PDF has no form fields.
    """
    if not _PDF_AVAILABLE:
        return {"error": "PyPDF2 is not installed"}
    try:
        reader = _PyPDF2.PdfReader(file_stream)
        data = {
            'page_count': len(reader.pages),
            'fields': reader.get_fields() or {},
            'metadata': dict(reader.metadata) if reader.metadata else {},
        }
        page_info = []
        for i, page in enumerate(reader.pages):
            try:
                page_info.append({
                    'page': i + 1,
                    'width': float(page.mediabox.width),
                    'height': float(page.mediabox.height),
                })
            except Exception:
                pass
        data['page_info'] = page_info
        return data
    except Exception as e:
        logger.error(f"PDF form data extraction error: {e}")
        return {"error": str(e)}


# ── Core processing functions ─────────────────────────────────────────────────

def validate_file(file):
    """
    Validate an uploaded file object.
    Returns (True, "File is valid") or (False, reason_string).
    """
    if not file or not file.filename:
        return False, "No file provided"

    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ('.docx', '.pdf', '.txt'):
        return False, "Only .docx, .pdf, and .txt files are supported"

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)

    if size == 0:
        return False, "File is empty"
    if size > 10 * 1024 * 1024:
        return False, "File must be under 10MB"

    return True, "File is valid"


def process_uploaded_file(file):
    """
    Process a validated uploaded file object and return a content dict:
        { 'file_type': str, 'text_content': str, ... }
    Raises ValueError for unsupported or unreadable files.
    """
    if not file or not file.filename:
        return None

    ext = os.path.splitext(file.filename.lower())[1]
    raw = file.read()
    if not raw:
        raise ValueError("File is empty")

    stream = io.BytesIO(raw)
    result = {}

    if ext == '.docx':
        if not _DOCX_AVAILABLE:
            raise RuntimeError(
                "DOCX upload received but python-docx is not installed. "
                "Add it to app/requirements.txt."
            )
        stream.seek(0)
        result['text_content'] = extract_text_from_docx(stream)
        stream.seek(0)
        result['xml_structure'] = extract_xml_from_docx(stream)
        result['file_type'] = 'docx'

    elif ext == '.pdf':
        if not _PDF_AVAILABLE:
            raise RuntimeError(
                "PDF upload received but PyPDF2 is not installed. "
                "Add it to app/requirements.txt."
            )
        stream.seek(0)
        result['text_content'] = extract_text_from_pdf(stream)
        stream.seek(0)
        result['form_data'] = extract_form_data_from_pdf(stream)
        result['file_type'] = 'pdf'

    elif ext == '.txt':
        result['text_content'] = raw.decode('utf-8', errors='replace')
        result['file_type'] = 'txt'

    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return result


def process_server_file(file_path):
    """
    Process a file stored on the server_files NAS volume.
    Returns the same content dict as process_uploaded_file, or None on failure.
    """
    if not os.path.exists(file_path):
        return None

    ext = os.path.splitext(file_path.lower())[1]
    result = {}

    try:
        if ext == '.docx':
            if not _DOCX_AVAILABLE:
                logger.warning(f"Skipping {file_path} — python-docx not installed")
                return None
            with open(file_path, 'rb') as f:
                stream = io.BytesIO(f.read())
            stream.seek(0)
            result['text_content'] = extract_text_from_docx(stream)
            stream.seek(0)
            result['xml_structure'] = extract_xml_from_docx(stream)
            result['file_type'] = 'docx'

        elif ext == '.pdf':
            if not _PDF_AVAILABLE:
                logger.warning(f"Skipping {file_path} — PyPDF2 not installed")
                return None
            with open(file_path, 'rb') as f:
                stream = io.BytesIO(f.read())
            stream.seek(0)
            result['text_content'] = extract_text_from_pdf(stream)
            stream.seek(0)
            result['form_data'] = extract_form_data_from_pdf(stream)
            result['file_type'] = 'pdf'

        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                result['text_content'] = f.read()
            result['file_type'] = 'txt'

        else:
            logger.warning(f"Unsupported server file type: {file_path}")
            return None

        return result

    except Exception as e:
        logger.error(f"Error processing server file {file_path}: {e}")
        return None


def load_server_files(page_name, directories=None):
    """
    Load and process all supported files from the server_files NAS volume
    for the given page.

    Args:
        page_name:    Current page name (always included as first directory).
        directories:  List of subdirectories to scan. Defaults to [page_name].

    Returns:
        dict mapping display-key → content dict.
        Keys are prefixed with directory name when loading from multiple dirs
        and the file is not in the page's own directory.
    """
    if directories is None:
        directories = [page_name]

    multi = len(directories) > 1
    server_files = {}

    for directory in directories:
        server_dir = f"/app/server_files/{directory}"
        if not os.path.exists(server_dir):
            logger.debug(f"server_files/{directory} not found — skipping")
            continue

        try:
            for filename in os.listdir(server_dir):
                file_path = os.path.join(server_dir, filename)
                if not os.path.isfile(file_path):
                    continue

                file_data = process_server_file(file_path)
                if not file_data:
                    continue

                base_key = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ')
                key = f"{directory} — {base_key}" if (multi and directory != page_name) else base_key

                if key in server_files:
                    logger.warning(f"Key conflict '{key}' — keeping first occurrence")
                    continue

                server_files[key] = file_data
                logger.info(f"Loaded server file: {directory}/{filename} → '{key}'")

        except Exception as e:
            logger.error(f"Error loading server_files/{directory}: {e}")
            continue

    logger.info(f"server_files loaded: {len(server_files)} files from {directories}")
    return server_files
