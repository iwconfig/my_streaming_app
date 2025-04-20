from app.extensions import celery, db
from app.models import Track, TrackStatus, ManifestType
from app.uploaders.base import UploaderError
# --- Import the new utility function ---
from app.utils import extract_audio_metadata
# --- End Import ---
from flask import current_app
import logging
import os
import subprocess
import shutil
import importlib
import json
import math

log = logging.getLogger(__name__)

# --- get_audio_duration_ms using ffprobe (can be kept as fallback or removed if mutagen is preferred) ---
def get_audio_duration_ms(filepath: str) -> int | None:
    """Uses ffprobe to get the duration of an audio file in milliseconds."""
    ffprobe_path = current_app.config.get('FFPROBE_PATH', 'ffprobe')
    command = [ ffprobe_path, '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', filepath ]
    log.debug(f"Running ffprobe command: {' '.join(command)}")
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        data = json.loads(result.stdout)
        log.debug(f"ffprobe output: {json.dumps(data, indent=2)}")
        duration_s = None
        if 'format' in data and 'duration' in data['format']:
            try: duration_s = float(data['format']['duration'])
            except (ValueError, TypeError): log.warning("Could not parse duration from format field.")
        if duration_s is None and 'streams' in data and data['streams']:
            for stream in data['streams']:
                if stream.get('codec_type') == 'audio' and 'duration' in stream:
                    try:
                        duration_s = float(stream['duration'])
                        break
                    except (ValueError, TypeError): log.warning("Could not parse duration from stream field.")
        if duration_s is not None and duration_s > 0:
            duration_ms = math.ceil(duration_s * 1000)
            log.info(f"Extracted duration via ffprobe: {duration_s:.3f}s ({duration_ms}ms)")
            return duration_ms
        else:
            log.warning(f"Could not find valid duration in ffprobe output for {filepath}")
            return None
    except FileNotFoundError: log.error(f"ffprobe command not found at '{ffprobe_path}'."); return None
    except subprocess.CalledProcessError as e: log.error(f"ffprobe failed for {filepath} (rc {e.returncode}): {e.stderr}"); return None
    except json.JSONDecodeError: log.error(f"Failed to parse ffprobe JSON output for {filepath}"); return None
    except Exception as e: log.error(f"Unexpected error getting ffprobe duration for {filepath}: {e}", exc_info=True); return None


# --- Helper Function: Load Uploader ---
def get_uploader_plugin(config):
    """Loads and instantiates the configured uploader plugin."""
    plugin_name = config.get('UPLOAD_PLUGIN', 'local').lower()
    log.info(f"Attempting to load uploader plugin: {plugin_name}")
    try:
        module_path = f"app.uploaders.{plugin_name}"
        uploader_module = importlib.import_module(module_path)
        class_name = f"{plugin_name.capitalize()}Uploader"
        uploader_class = getattr(uploader_module, class_name)
        log.info(f"Successfully loaded uploader class: {class_name}")
        return uploader_class(config)
    except (ImportError, AttributeError) as e:
        log.error(f"Failed to load uploader plugin '{plugin_name}': {e}", exc_info=True)
        raise ImportError(f"Could not find or load uploader plugin: {plugin_name}")


# --- Main Celery Task ---
@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def process_audio_task(self, track_id: int, temp_input_path: str, output_format: str = 'HLS'):
    """
    Celery task to process an uploaded audio file:
    1. Extract metadata, update status to PROCESSING.
    2. Run FFmpeg (if enabled) using configured parameters for HLS or DASH.
    3. Upload results using configured plugin.
    4. Update track status to READY or ERROR.
    5. Clean up temporary files.
    """
    log.info(f"Starting audio processing task for track_id: {track_id}, input: {temp_input_path}, format: {output_format}")
    track = db.session.get(Track, track_id)
    task_successful = False # Flag to track success for finally block
    if not track:
        log.error(f"Task failed: Track with ID {track_id} not found.")
        if os.path.exists(temp_input_path):
             try: os.remove(temp_input_path); log.info(f"Removed orphaned temp input file: {temp_input_path}")
             except OSError as e: log.error(f"Error removing orphaned temp file {temp_input_path}: {e}")
        return

    # --- 1. Extract Metadata & Update Status ---
    log.info(f"Extracting metadata for track {track_id} from {temp_input_path}")
    extracted_meta = extract_audio_metadata(temp_input_path)

    # Merge metadata: Use extracted only if not provided by user initially
    if not track.title and extracted_meta.get('title'):
        track.title = extracted_meta['title']
        log.debug(f"Using extracted title for track {track_id}: {track.title}")
    if not track.artist and extracted_meta.get('artist'):
        track.artist = extracted_meta['artist']
        log.debug(f"Using extracted artist for track {track_id}: {track.artist}")
    if not track.album and extracted_meta.get('album'):
        track.album = extracted_meta['album']
        log.debug(f"Using extracted album for track {track_id}: {track.album}")
    if track.track_number is None and extracted_meta.get('tracknumber'):
        track.track_number = extracted_meta['tracknumber']
        log.debug(f"Using extracted track number for track {track_id}: {track.track_number}")

    # Always use extracted duration if available from mutagen
    if extracted_meta.get('duration_ms'):
        track.duration_ms = extracted_meta['duration_ms']
        log.debug(f"Using extracted duration for track {track_id}: {track.duration_ms}ms")
    # Fallback to ffprobe duration if mutagen failed and DB doesn't have it
    elif track.duration_ms is None:
         log.info("Mutagen did not provide duration, trying ffprobe...")
         ffprobe_duration_ms = get_audio_duration_ms(temp_input_path)
         if ffprobe_duration_ms:
             track.duration_ms = ffprobe_duration_ms
             log.debug(f"Using ffprobe duration for track {track_id}: {track.duration_ms}ms")
         else:
             log.warning(f"Could not determine duration for track {track_id} using mutagen or ffprobe.")

    # Set status and commit changes
    track.status = TrackStatus.PROCESSING
    track.error_message = None
    try:
        db.session.commit()
        log.info(f"Track {track_id} status set to PROCESSING. Metadata updated. Duration: {track.duration_ms}ms")
    except Exception as e:
         log.error(f"Failed to update track {track_id} metadata/status: {e}", exc_info=True)
         db.session.rollback()
         raise self.retry(exc=e, countdown=int(self.default_retry_delay * (2 ** self.request.retries)))

    # --- Define Processing Output Path ---
    processing_output_dir = os.path.join( current_app.config['LOCAL_STORAGE_OUTPUT_DIR'], str(track.user_id), str(track.id) )
    try:
        os.makedirs(processing_output_dir, exist_ok=True)
        log.info(f" Ensured processing output directory exists: {processing_output_dir}")
    except OSError as e:
        log.error(f"Cannot create processing output directory {processing_output_dir}: {e}")
        track.status = TrackStatus.ERROR; track.error_message = f"Cannot create output directory: {e}"; db.session.commit()
        return

    manifest_name_base = "manifest"
    final_manifest_type = None
    ffmpeg_success = False
    try:
        # --- 2. Run FFmpeg (Configurable) ---
        if current_app.config.get('FFMPEG_ENABLED', False):
            log.info(f"Running FFmpeg for track {track_id} in format {output_format}...")
            ffmpeg_path = current_app.config['FFMPEG_PATH']
            codec = current_app.config['FFMPEG_DEFAULT_AUDIO_CODEC']; bitrate = current_app.config['FFMPEG_DEFAULT_AUDIO_BITRATE']
            seg_duration = current_app.config['FFMPEG_DEFAULT_SEGMENT_DURATION']; allowed_formats = current_app.config.get('FFMPEG_ALLOWED_FORMATS', ['HLS', 'DASH'])
            if output_format not in allowed_formats: raise ValueError(f"Unsupported output format '{output_format}' specified for processing.")
            if output_format == 'HLS':
                final_manifest_type = ManifestType.HLS; manifest_filename = f"{manifest_name_base}.m3u8"
                manifest_filepath = os.path.join(processing_output_dir, manifest_filename)
                segment_filename_template = os.path.join(processing_output_dir, "segment%03d.ts")
                cmd = [ ffmpeg_path, '-y', '-i', temp_input_path, '-map', '0:a:0', '-c:a', codec, '-b:a', bitrate, '-f', 'hls', '-hls_time', str(seg_duration), '-hls_list_size', '0', '-hls_segment_filename', segment_filename_template, '-start_number', '0', manifest_filepath ]
            elif output_format == 'DASH':
                final_manifest_type = ManifestType.DASH; manifest_filename = f"{manifest_name_base}.mpd"
                manifest_filepath = os.path.join(processing_output_dir, manifest_filename)
                init_segment_name = os.path.join(processing_output_dir, "init-stream$RepresentationID$.m4s")
                media_segment_name = os.path.join(processing_output_dir, "chunk-stream$RepresentationID$-$Number%05d$.m4s")
                cmd = [ ffmpeg_path, '-y', '-i', temp_input_path, '-map', '0:a:0', '-c:a', codec, '-b:a', bitrate, '-f', 'dash', '-seg_duration', str(seg_duration), '-use_template', '1', '-use_timeline', '1', '-init_seg_name', init_segment_name, '-media_seg_name', media_segment_name, manifest_filepath ]
            else: raise ValueError(f"Internal error: Reached FFmpeg step with invalid format: {output_format}")
            log.debug(f"Executing FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            log.info(f"FFmpeg processing to {output_format} completed successfully for track {track_id}."); log.debug(f"FFmpeg stderr:\n{result.stderr}")
            ffmpeg_success = True
        else: log.warning("FFmpeg processing is disabled by config."); raise RuntimeError("FFmpeg processing is disabled, cannot generate segments.")
        if ffmpeg_success and final_manifest_type:
            uploader = get_uploader_plugin(current_app.config)
            log.info(f"Uploading processed files for track {track_id} using '{uploader.__class__.__name__}'")
            final_manifest_url, _ = uploader.upload( source_dir=processing_output_dir, user_id=track.user_id, track_id=track.id )
            log.info(f"Upload complete for track {track_id}. Manifest URL: {final_manifest_url}")
            track.status = TrackStatus.READY; track.manifest_url = final_manifest_url
            track.manifest_type = final_manifest_type; track.error_message = None
            db.session.commit(); log.info(f"Track {track_id} status updated to READY.")
            uploader.cleanup_source(processing_output_dir)
            task_successful = True # Mark as successful
        else: raise RuntimeError("Internal logic error: FFmpeg success/format type not correctly set.")
    except (subprocess.CalledProcessError, RuntimeError, ValueError, ImportError, FileNotFoundError, UploaderError) as e:
        log.error(f"Caught processing/upload error for track {track_id}: {type(e).__name__} - {e}", exc_info=False)
        db.session.rollback()
        track_in_error = db.session.get(Track, track_id)
        if track_in_error:
            error_detail = str(e)
            if isinstance(e, subprocess.CalledProcessError) and e.stderr: error_detail += f" | STDERR: {e.stderr[:500]}"
            track_in_error.status = TrackStatus.ERROR
            track_in_error.error_message = f"{type(e).__name__}: {error_detail[:950]}"
            db.session.commit()
            log.info(f"Track {track_id} status updated to ERROR due to {type(e).__name__}.")
        else: log.error(f"Could not update track {track_id} status to ERROR after exception.")
        log.warning(f"Keeping processing directory for debugging: {processing_output_dir}")
        try:
            retry_delay = int(self.default_retry_delay * (2 ** self.request.retries))
            log.warning(f"Retrying task for track {track_id} due to {type(e).__name__} (attempt {self.request.retries + 1}/{self.max_retries}) in {retry_delay}s")
            raise self.retry(exc=e, countdown=retry_delay)
        except self.MaxRetriesExceededError: log.error(f"Max retries exceeded for track {track_id}. Final status is ERROR.")
        except Exception as retry_e: log.error(f"Unexpected error during task retry mechanism for track {track_id}: {retry_e}", exc_info=True)
    except Exception as e:
         log.critical(f"Caught UNEXPECTED error processing track {track_id}: {e}", exc_info=True)
         db.session.rollback()
         try:
             track_unexpected_error = db.session.get(Track, track_id)
             if track_unexpected_error:
                 track_unexpected_error.status = TrackStatus.ERROR
                 track_unexpected_error.error_message = f"Unexpected Error: {str(e)[:900]}"
                 db.session.commit()
         except Exception as db_err: log.error(f"Failed even to mark track {track_id} as ERROR after unexpected exception: {db_err}")
    finally:
        # Only remove input file on success or if track was initially missing
        if task_successful or not track:
            if os.path.exists(temp_input_path):
                try: os.remove(temp_input_path); log.info(f"Removed temporary input file: {temp_input_path}")
                except OSError as e: log.error(f"Failed to remove temporary input file {temp_input_path}: {e}")
        else:
            log.warning(f"Keeping temporary input file due to task failure/retry: {temp_input_path}")
