from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import uuid
import logging # Use Flask/Python logging

from app.models import Track, ManifestType, TrackStatus
from app.schemas import (
    TrackSchema, TrackLoadURLSchema, TrackUpdateSchema, TrackUploadMetadataSchema
)
from app.extensions import db, celery
# Import task dynamically later or define placeholder if needed for structure
# from app.tasks import process_audio_task # We'll create this next

from marshmallow import ValidationError

# Setup logger
log = logging.getLogger(__name__)

bp = Blueprint('tracks', __name__)
track_schema = TrackSchema()
tracks_schema = TrackSchema(many=True)
track_load_url_schema = TrackLoadURLSchema()
track_upload_metadata_schema = TrackUploadMetadataSchema()
track_update_schema = TrackUpdateSchema()


# --- Endpoint for adding by providing a manifest URL directly ---
@bp.route('/add_by_url', methods=['POST']) # Renamed route
@jwt_required()
def add_track_by_url():
    current_user_id = int(get_jwt_identity())
    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input data provided"}), 400

    try:
        # Use the specific schema for URL loading
        data = track_load_url_schema.load(json_data)
    except ValidationError as err:
        log.warning(f"Validation failed for add_track_by_url: {err.messages}")
        return jsonify({"validation_errors": err.messages}), 400

    # Create track marked as READY since URL is provided
    new_track = Track(
        user_id=current_user_id,
        title=data['title'],
        artist=data.get('artist'),
        album=data.get('album'),
        track_number=data.get('track_number'),
        duration_ms=data.get('duration_ms'),
        manifest_url=data['manifest_url'],
        manifest_type=data['manifest_type'],
        status=TrackStatus.READY # Mark as ready
    )

    try:
        db.session.add(new_track)
        db.session.commit()
        log.info(f"Track {new_track.id} added by URL for user {current_user_id}")
        return jsonify(track_schema.dump(new_track)), 201
    except Exception as e:
        db.session.rollback()
        log.error(f"Error adding track by URL: {e}", exc_info=True)
        return jsonify({"message": "Could not add track", "error": str(e)}), 500


# --- NEW Endpoint for Uploading Audio Files for Processing ---
@bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_track_file():
    # Check if processing is enabled in config
    if not current_app.config.get('PROCESSING_ENABLED', False):
         log.warning("Upload attempt failed: Processing is disabled globally.")
         return jsonify({"message": "File uploads and processing are currently disabled."}), 403 # Forbidden

    current_user_id = int(get_jwt_identity())

    # Check for file part
    if 'audio_file' not in request.files:
        log.warning("Upload failed: No 'audio_file' part in request.")
        return jsonify({"message": "Missing 'audio_file' part in the request"}), 400
    file = request.files['audio_file']
    if not file or file.filename == '':
        log.warning("Upload failed: No file selected.")
        return jsonify({"message": "No file selected"}), 400

    # Validate metadata from form data
    try:
        form_data = request.form.to_dict()
        log.debug(f"Received form data for upload: {form_data}")
        metadata = track_upload_metadata_schema.load(form_data)
        # --- Get the desired output format ---
        output_format = metadata.get('output_format', 'HLS').upper() # Default to HLS if schema default fails? or rely on schema
        log.info(f"Requested output format: {output_format}")

        # --- Validate requested format against allowed formats in config ---
        allowed_formats = current_app.config.get('FFMPEG_ALLOWED_FORMATS', ['HLS', 'DASH'])
        if output_format not in allowed_formats:
             log.warning(f"Upload rejected: Unsupported output_format '{output_format}' requested.")
             return jsonify({"message": f"Unsupported output_format. Allowed formats: {', '.join(allowed_formats)}"}), 400

    except ValidationError as err:
        log.warning(f"Upload validation failed (metadata): {err.messages}")
        return jsonify({"validation_errors": err.messages}), 400

    # Secure filename and create unique temp path
    original_filename = secure_filename(file.filename)
    _, file_extension = os.path.splitext(original_filename)
    # Generate unique name to avoid collisions and hide original name
    temp_filename = f"{uuid.uuid4().hex}{file_extension}"
    temp_filepath = os.path.join(current_app.config['UPLOAD_TEMP_DIR'], temp_filename)

    try:
        log.info(f"Saving uploaded file '{original_filename}' to '{temp_filepath}'")
        file.save(temp_filepath)
    except Exception as e:
        log.error(f"Failed to save uploaded file: {e}", exc_info=True)
        return jsonify({"message": "Failed to save uploaded file"}), 500

    # Create Track entry in DB with PENDING status
    new_track = Track(
        user_id=current_user_id,
        title=metadata['title'],
        artist=metadata.get('artist'),
        album=metadata.get('album'),
        track_number=metadata.get('track_number'),
        status=TrackStatus.PENDING # Initial status
    )

    track_id = None # Define track_id outside try block
    try:
        db.session.add(new_track)
        db.session.commit()
        track_id = new_track.id # Get the ID after commit
        log.info(f"Created track record ID {track_id} for user {current_user_id}, status: PENDING")
    except Exception as e:
        db.session.rollback()
        log.error(f"Failed to create track record in DB: {e}", exc_info=True)
        # Clean up the saved temp file if DB insert fails
        if os.path.exists(temp_filepath):
             try:
                 os.remove(temp_filepath)
                 log.info(f"Removed temporary file due to DB error: {temp_filepath}")
             except OSError as remove_err:
                 log.error(f"Failed to remove temporary file {temp_filepath}: {remove_err}")
        return jsonify({"message": "Failed to create track record"}), 500

    # --- Send task to Celery ---
    # Ensure track_id was obtained
    if track_id:
        try:
            # Dynamically import the task function only when needed
            # Avoids circular imports if tasks.py imports models/db etc.
            from app.tasks import process_audio_task
            log.info(f"Queueing processing task for track ID: {track_id}, file: {temp_filepath}, format: {output_format}")
            # Pass track ID and the *full path* to the temporary file
            process_audio_task.delay(
                track_id=track_id,
                temp_input_path=temp_filepath,
                output_format=output_format # Pass the format
            )
        except ImportError:
             log.error("Could not import process_audio_task. Celery tasks might not be configured correctly.")
             # Rollback DB change and cleanup file? Or mark track as ERROR?
             # For now, mark as ERROR.
             new_track.status = TrackStatus.ERROR
             new_track.error_message = "Backend configuration error: Could not queue processing task."
             db.session.commit()
             # No need to delete temp file here, maybe needed for manual retry?
             return jsonify({"message": "Internal configuration error preventing processing."}), 500
        except Exception as e:
            log.error(f"Failed to queue Celery task for track {track_id}: {e}", exc_info=True)
            # Mark track as error
            new_track.status = TrackStatus.ERROR
            new_track.error_message = f"Failed to queue processing task: {e}"
            db.session.commit()
            # No need to delete temp file here
            return jsonify({"message": "Failed to queue background processing task"}), 500
    else:
        # Should not happen if DB commit succeeded, but defensively:
        log.error("Track ID was not obtained after DB commit, cannot queue task.")
        if os.path.exists(temp_filepath): # Cleanup file if we can't process
             os.remove(temp_filepath)
        return jsonify({"message": "Internal error obtaining track ID after save."}), 500


    # Return 202 Accepted: request received, processing started in background
    # Include the current state of the track (PENDING)
    return jsonify(track_schema.dump(new_track)), 202


# --- GET Track List (Added status filtering) ---
@bp.route('', methods=['GET'])
@jwt_required()
def get_tracks():
    current_user_id = int(get_jwt_identity())
    status_filter = request.args.get('status') # e.g., ?status=READY

    query = Track.query.filter_by(user_id=current_user_id)

    if status_filter:
        status_str = status_filter.upper()
        if hasattr(TrackStatus, status_str):
            status_enum = TrackStatus[status_str]
            query = query.filter(Track.status == status_enum)
        else:
            valid_statuses = [s.name for s in TrackStatus]
            log.warning(f"Invalid status filter '{status_filter}' received.")
            return jsonify({"message": f"Invalid status filter value. Valid options: {valid_statuses}"}), 400

    # Consistent ordering
    user_tracks = query.order_by(Track.added_at.desc()).all()
    return jsonify(tracks_schema.dump(user_tracks)), 200


# --- GET Specific Track (Includes status) ---
@bp.route('/<int:track_id>', methods=['GET'])
@jwt_required()
def get_track(track_id):
    current_user_id = int(get_jwt_identity())
    track = db.session.get(Track, track_id) # Use session.get

    if not track or track.user_id != current_user_id:
        return jsonify({"message": "Track not found or access denied"}), 404

    return jsonify(track_schema.dump(track)), 200 # Returns status etc.

# --- GET Track Status Only ---
@bp.route('/<int:track_id>/status', methods=['GET'])
@jwt_required()
def get_track_status(track_id):
    current_user_id = int(get_jwt_identity())
    track = db.session.get(Track, track_id)

    if not track or track.user_id != current_user_id:
        return jsonify({"message": "Track not found or access denied"}), 404

    # Return subset of info
    return jsonify({
        "id": track.id,
        "status": track.status.value,
        "error_message": track.error_message
    }), 200

# --- PUT Track (Update Metadata ONLY) ---
@bp.route('/<int:track_id>', methods=['PUT'])
@jwt_required()
def update_track(track_id):
    current_user_id = int(get_jwt_identity())
    track = db.session.get(Track, track_id)

    if not track or track.user_id != current_user_id:
        return jsonify({"message": "Track not found or access denied"}), 404

    # Prevent updates if track is currently processing? Optional, but maybe safer.
    # if track.status == TrackStatus.PROCESSING:
    #     return jsonify({"message": "Cannot update track while it is processing"}), 409

    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input data provided"}), 400

    try:
        # Use update schema, partial=True allows updating only provided fields
        data = track_update_schema.load(json_data, partial=True)
    except ValidationError as err:
        log.warning(f"Update validation failed for track {track_id}: {err.messages}")
        return jsonify({"validation_errors": err.messages}), 400

    # Update allowed fields
    allowed_fields = ['title', 'artist', 'album', 'track_number']
    updated = False
    for key, value in data.items():
        if key in allowed_fields:
            setattr(track, key, value)
            updated = True

    if not updated:
        return jsonify({"message": "No updatable fields provided"}), 400

    try:
        db.session.commit()
        log.info(f"Updated metadata for track {track_id}")
        return jsonify(track_schema.dump(track)), 200
    except Exception as e:
        db.session.rollback()
        log.error(f"Error updating track {track_id}: {e}", exc_info=True)
        return jsonify({"message": "Could not update track", "error": str(e)}), 500

# --- DELETE Track ---
@bp.route('/<int:track_id>', methods=['DELETE'])
@jwt_required()
def delete_track(track_id):
    current_user_id = int(get_jwt_identity())
    track = db.session.get(Track, track_id)

    if not track or track.user_id != current_user_id:
        return jsonify({"message": "Track not found or access denied"}), 404

    # TODO: Advanced - If track is PROCESSING, try to cancel the Celery task?
    # Needs task ID storage and Celery's revoke capabilities.

    # TODO: Advanced - Delete associated files from storage (local, teldrive, etc.)
    # This might require another background task or direct deletion logic here.
    # For now, we just delete the DB record.

    try:
        # Relationship cascade should handle removal from playlists
        db.session.delete(track)
        db.session.commit()
        log.info(f"Deleted track {track_id} for user {current_user_id}")
        return jsonify({"message": "Track deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        log.error(f"Error deleting track {track_id}: {e}", exc_info=True)
        return jsonify({"message": "Could not delete track", "error": str(e)}), 500
