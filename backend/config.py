import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:
    # --- Core App Config ---
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key_dev') # CHANGE THIS IN PRODUCTION
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'another_secret_key_dev') # CHANGE THIS IN PRODUCTION

    # --- Database Config ---
    # Default to a local SQLite file if DATABASE_URL is not set in .env
    DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'app.db') # DB in data subdirectory
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{DEFAULT_SQLITE_PATH}')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Celery Configuration ---
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    CELERY_IMPORTS = ('app.tasks',)

    # --- File Handling & Processing Configuration ---
    # Base directory to temporarily store uploaded files before processing
    UPLOAD_TEMP_DIR = os.environ.get('UPLOAD_TEMP_DIR', os.path.join(os.path.dirname(__file__), 'data', 'temp_uploads'))
    # Base directory where FFmpeg will write final segmented output for the 'local' uploader
    LOCAL_STORAGE_OUTPUT_DIR = os.environ.get('LOCAL_STORAGE_OUTPUT_DIR', os.path.join(os.path.dirname(__file__), 'data', 'processed_audio'))
    # Base URL corresponding to LOCAL_STORAGE_OUTPUT_DIR
    LOCAL_STORAGE_URL_BASE = os.environ.get('LOCAL_STORAGE_URL_BASE', '/processed/')

    # Path to the ffmpeg executable
    FFMPEG_PATH = os.environ.get('FFMPEG_PATH', 'ffmpeg') # Assumes ffmpeg is in system PATH

    # --- Plugin Configuration ---
    # Selects the uploader plugin to use after processing. 'local' is currently the only option.
    UPLOAD_PLUGIN = os.environ.get('UPLOAD_PLUGIN', 'local')

    # --- Processing Flags ---
    # Global switch to enable/disable background processing via Celery
    PROCESSING_ENABLED = os.environ.get('PROCESSING_ENABLED', 'true').lower() == 'true'
    # Specific flag for FFmpeg step (allows disabling just FFmpeg if needed for testing)
    FFMPEG_ENABLED = os.environ.get('FFMPEG_ENABLED', 'true').lower() == 'true'

    # --- FFmpeg Configuration ---
    FFMPEG_PATH = os.environ.get('FFMPEG_PATH', 'ffmpeg')
    FFPROBE_PATH = os.environ.get('FFPROBE_PATH', 'ffprobe') # Add ffprobe path
    # Default processing parameters (can be overridden per request if needed later)
    FFMPEG_DEFAULT_AUDIO_CODEC = os.environ.get('FFMPEG_DEFAULT_AUDIO_CODEC', 'aac')
    FFMPEG_DEFAULT_AUDIO_BITRATE = os.environ.get('FFMPEG_DEFAULT_AUDIO_BITRATE', '192k')
    FFMPEG_DEFAULT_SEGMENT_DURATION = os.environ.get('FFMPEG_DEFAULT_SEGMENT_DURATION', '10')
    # Allowable output formats (maps to ManifestType enum values)
    FFMPEG_ALLOWED_FORMATS = os.environ.get('FFMPEG_ALLOWED_FORMATS', 'HLS,DASH').split(',')
