from flask import Blueprint, send_from_directory, current_app, abort, Response
import os
import logging
import mimetypes

log = logging.getLogger(__name__)
bp = Blueprint('media', __name__)

@bp.route('/processed/<path:filepath>')
def serve_processed_media(filepath):
    """Serves files from LOCAL_STORAGE_OUTPUT_DIR - DEVELOPMENT ONLY."""
    log.info("=== Media Request ===")
    log.info(f"Requested filepath: {filepath}")
    
    # Get the configured path
    configured_dir = current_app.config.get('LOCAL_STORAGE_OUTPUT_DIR')
    if not configured_dir:
        log.error("LOCAL_STORAGE_OUTPUT_DIR not configured.")
        abort(500)
    
    log.info(f"Configured directory: {configured_dir}")

    # Resolve the path relative to the backend directory
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    media_dir = os.path.abspath(os.path.join(backend_dir, configured_dir.lstrip('./')))
    full_path = os.path.join(media_dir, filepath)
    
    log.info(f"Backend directory: {backend_dir}")
    log.info(f"Media directory: {media_dir}")
    log.info(f"Full file path: {full_path}")
    log.info(f"File exists: {os.path.exists(full_path)}")
    
    # Basic security check
    if '..' in filepath or filepath.startswith('/'):
        log.warning(f"Attempted directory traversal: {filepath}")
        abort(404)

    try:
        if not os.path.exists(full_path):
            log.error(f"File not found at path: {full_path}")
            abort(404)
            
        # Determine correct mime type
        mime_type, _ = mimetypes.guess_type(filepath)
        if filepath.endswith('.m3u8'):
            mime_type = 'application/vnd.apple.mpegurl'
        elif filepath.endswith('.ts'):
            mime_type = 'video/mp2t'
            
        log.info(f"Serving file with mime type: {mime_type}")
        
        # Use send_from_directory with explicit mime type
        response = send_from_directory(media_dir, filepath, 
                                    as_attachment=False,
                                    mimetype=mime_type)
        
        # Add CORS headers for media files
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
        
    except Exception as e:
        log.error(f"Error serving file {filepath}: {e}", exc_info=True)
        abort(500)
