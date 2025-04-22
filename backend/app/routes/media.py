from flask import Blueprint, send_from_directory, current_app, abort
import os
import logging

log = logging.getLogger(__name__)
bp = Blueprint('media', __name__)

@bp.route('/processed/<path:filepath>')
def serve_processed_media(filepath):
    """Serves files from LOCAL_STORAGE_OUTPUT_DIR - DEVELOPMENT ONLY."""
    # Get the configured path (might be relative like './processed_audio')
    configured_dir = current_app.config.get('LOCAL_STORAGE_OUTPUT_DIR')
    if not configured_dir:
        log.error("LOCAL_STORAGE_OUTPUT_DIR not configured.")
        abort(500)

    # --- Ensure the directory path is absolute ---
    # os.path.abspath resolves it relative to the current working directory
    # If config value is already absolute, abspath does nothing harmful.
    media_dir = os.path.abspath(configured_dir)
    # --- End modification ---

    # Basic security check (already present)
    if '..' in filepath or filepath.startswith('/'):
         log.warning(f"Attempted directory traversal: {filepath}")
         abort(404)

    log.debug(f"Attempting to serve file: {filepath} from absolute directory: {media_dir}")
    try:
        # send_from_directory should now work with the absolute media_dir
        return send_from_directory(media_dir, filepath, as_attachment=False)
    except FileNotFoundError:
         log.warning(f"File not found by send_from_directory: {os.path.join(media_dir, filepath)}")
         abort(404)
    except Exception as e:
         log.error(f"Error serving file {filepath}: {e}", exc_info=True)
         abort(500)
