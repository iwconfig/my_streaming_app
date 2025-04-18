# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
