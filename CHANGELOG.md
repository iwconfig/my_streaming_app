# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-04-20

### Added

*   **Audio File Upload & Processing:**
    *   New `/api/tracks/upload` endpoint for uploading raw audio files.
    *   Integrated Celery and Redis for background processing of uploads.
    *   Added `app/tasks.py` with `process_audio_task` for background jobs.
*   **FFmpeg Segmentation:**
    *   Celery task now uses FFmpeg to segment uploaded audio into HLS or DASH formats.
    *   Output format (HLS/DASH) can be specified during upload.
    *   FFmpeg parameters (codec, bitrate, segment duration, paths) are configurable via `.env`/`config.py`.
*   **Metadata & Status:**
    *   Integrated `mutagen` to extract common tags (title, artist, album, track number, duration) from uploaded files via `app/utils.py`.
    *   Integrated `ffprobe` as a fallback for duration extraction.
    *   Extracted metadata populates track details if not provided by the user during upload (duration is always updated if found).
    *   Added `status` field to `Track` model (`PENDING`, `PROCESSING`, `READY`, `ERROR`).
    *   Added `error_message` field to `Track` model.
    *   Added `/api/tracks/<id>/status` endpoint to query processing status.
*   **Storage Plugin System:**
    *   Created base architecture for swappable storage backends (`app/uploaders/`).
    *   Implemented `LocalUploader` plugin as the default, saving files to `LOCAL_STORAGE_OUTPUT_DIR`.
    *   Made the active uploader plugin configurable via `UPLOAD_PLUGIN`.
*   **Configuration:**
    *   Added various configuration options for Celery, file paths, FFmpeg, etc.
    *   Database connection is configurable via `DATABASE_URL`, defaulting to local SQLite (`app_data.db`).
*   **Development:**
    *   Added development-only media server (`app/routes/media.py`) to serve processed files locally when `FLASK_DEBUG=1`.
    *   Added `celery_app.py` for reliable worker task discovery.
*   **Testing:**
    *   Added tests for the new `/upload` and `/status` endpoints.
    *   Added extensive unit tests for `app/tasks.py` (including metadata extraction, FFmpeg command building simulation, uploader interaction, error handling, and retries) using mocks.
    *   Configured tests for eager Celery execution and in-memory broker/backend.
*   **File Management:**
    *   Added basic synchronous deletion of processed files/directory when a track is deleted via the API (for local uploader).
    *   Added cleanup of temporary upload files within the Celery task.

### Changed

*   Renamed original track creation endpoint from `POST /api/tracks` to `POST /api/tracks/add_by_url`.
*   `Track` model fields `manifest_url` and `manifest_type` are now nullable (populated after processing).
*   Set `native_enum=False` on `db.Enum` columns in models for better cross-database compatibility (PostgreSQL, SQLite, MySQL). (Applied via new migration).
*   Track list (`GET /api/tracks`) can now be filtered by `?status=...`.
*   Refactored schemas (`app/schemas/track.py`) to support separate URL and upload creation paths.
*   Updated database migrations to reflect model changes.

### Fixed

*   Resolved various `pytest` setup and mocking issues, particularly around Celery task testing in eager mode.
*   Corrected file path handling in tests and development server.

## [0.1.0] - 2025-04-18

### Added

*   User registration and JWT-based authentication (`/api/auth/register`, `/api/auth/login`, `/api/auth/me`).
*   Core database models: `User`, `Track`, `Playlist`, `playlist_tracks` (many-to-many association).
*   Track model requires user to provide `manifest_url` and `manifest_type` (HLS/DASH).
*   API endpoints for CRUD operations on Tracks (owned by user) via `POST /api/tracks` (for creation), GET `/api/tracks`, GET/PUT/DELETE `/api/tracks/<id>`.
*   API endpoints for CRUD operations on Playlists (owned by user) via `/api/playlists`.
*   API endpoints for adding, removing, viewing, and reordering tracks within playlists.
*   Basic Flask application structure using Application Factory pattern.
*   SQLAlchemy ORM integration.
*   Flask-Migrate for database schema migrations (initially targeting PostgreSQL).
*   Marshmallow schemas for API data serialization and validation (`app/schemas`).
*   Core Flask extensions configured (`Flask-SQLAlchemy`, `Flask-Migrate`, `Flask-JWT-Extended`, `Flask-Bcrypt`, `Flask-Marshmallow`, `Flask-Cors`).
*   Basic configuration loading from `.env` file via `config.py`.
*   Initial test suite setup with `pytest` and `pytest-flask` using SQLite (`tests/`).
