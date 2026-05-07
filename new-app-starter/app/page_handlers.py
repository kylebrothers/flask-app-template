"""
app/page_handlers.py — App-specific page handler overrides.

This file overrides the template's page_handlers.py. You have two options:

OPTION A — Full override (replace both handlers):
    Implement handle_claude_call_page and handle_no_call_page from scratch.
    Use this when your app needs fundamentally different logic.

OPTION B — Partial override (extend one or both handlers):
    Import the base handlers and wrap them with pre/post logic.

    Example:
        from page_handlers import (
            handle_claude_call_page as _base_claude,
            handle_no_call_page as _base_no_call,
            build_claude_prompt,
        )

        def handle_claude_call_page(page_name, form_data, uploaded_files_data,
                                     server_files_data, session_id, claude_client):
            # Pre-processing
            form_data['injected_context'] = 'some extra context'
            # Call base handler
            return _base_claude(page_name, form_data, uploaded_files_data,
                                server_files_data, session_id, claude_client)

For most apps, Option B is sufficient. Delete this file entirely if you don't
need any custom handler logic — the template's page_handlers.py will be used.
"""

# PLACEHOLDER: Implement or extend handlers as needed.
# If this file stays empty, delete it so the template version is used instead.

# from page_handlers import handle_claude_call_page as _base_claude  # noqa
# from page_handlers import handle_no_call_page as _base_no_call      # noqa
