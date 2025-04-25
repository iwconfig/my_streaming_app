### General

Rules:
- Always start with a clear plan before diving into code.
- Break down tasks into manageable chunks.
- Use comments to outline the purpose of each section of code.
- Regularly review and refactor code to maintain clarity and efficiency.
- Follow the established project structure for both frontend and backend.
- Keep frontend and backend code separate to maintain clarity.
- Use consistent naming conventions for files and directories.
- Organize code logically, grouping related files together.
- Use version control (e.g., Git) to track changes and collaborate effectively.
- Regularly commit changes with clear messages.
- Use branches for new features or bug fixes to keep the main branch stable.
- Merge branches only after thorough testing and code review.
- Document any significant changes in the CHANGELOG.md file, but avoid excessive detail.
  * Do not include trivial changes or minor fixes, and avoid documenting changes that are already clear from the code itself.
  * Provide a high-level overview of changes, focusing on new features, major improvements, and important fixes.
  * Follow https://keepachangelog.com/en/1.1.0/ for formatting and structure.
  * If you revert an uncommitted changeset, do not document it in the changelog.
- Use comments and documentation to explain complex code or decisions.
- Keep documentation up to date with code changes.

## Changelog Policy

- Only document actual, committed, and significant changes to code or configuration in the CHANGELOG.md file.
- Do **not** include:
  - Notes about mistakes, or reverted uncommitted changes.
  - Process notes, intentions, or "next steps."
  - Excessive detail about minor or trivial changes.
- Each changelog entry should be a concise summary of what was added, changed, or removed, compared to the last committed state.
- If a change is reverted before being committed, do **not** document it in the changelog.

**Example of good changelog entries:**
- Added authentication screens and API integration to frontend.
- Updated Dockerfile to use persistent Android SDK directory for builds.
- Refactored track list UI for better responsiveness.

**Example of what NOT to include:**
- Removed a file that was a mistake (if it was never committed).
- Notes about future plans or "next steps."
- Documentation of changes that were reverted before commit.

## UI

Rules:
- Always use Svelte with Tailwind CSS for building UI components.
- Use modern styling and layouts that adapt beautifully on both desktop and mobile browsers.
- Avoid mixing in any non-cross-platform components; all UI should be implemented in Svelte.
- Ensure all UI components are responsive and visually appealing on modern devices.

## Build & Run

### Frontend

Run in docker container for all frontend commands. This ensures that the environment is consistent and avoids issues with local dependencies.

Always build and run the app after making any code changes to verify functionality.

#### To Build the App

Use the Svelte (or SvelteKit) CLI to build the project:

- **Development:**
  ```shell
  npm run dev
  ```
- **Production Build:**
  ```shell
  npm run build
  ```

#### To Run the App

- **Development:**
  ```shell
  npm run dev
  ```
- **Production Preview:**
  ```shell
  npm run preview
  ```

### Backend

The backend does **not** use Docker. All backend work must be performed within the Python virtual environment located at `./venv`.

#### Backend Setup

1. Create the virtual environment (if not already present):

    ```shell
    python3 -m venv ./venv
    ```

2. Activate the virtual environment:

    - On Linux/macOS:
      ```shell
      source ./venv/bin/activate
      ```
    - On Windows:
      ```shell
      ./venv/Scripts/activate
      ```

3. Install backend dependencies:

    ```shell
    pip install -r ./backend/requirements.txt
    ```

#### Running the Backend

- Flask server (uses `.flaskenv` in `./backend` for configuration):

    ```shell
    cd ./backend
    flask run -h 0.0.0.0
    ```

- Celery worker:

    ```shell
    cd ./backend
    celery -A celery_app.celery worker --loglevel=info
    ```

## Backend Integration

- The backend is powered by Python Flask and Python Celery.
- Ensure that any backend work is performed within the project's Python virtual environment; this virtual environment is located at ./venv.
- Activate the virtual environment with:
  ```shell
  source ./venv/bin/activate
  ```
  (On Windows, use `./venv/Scripts/activate`.)
- Verify that API calls made from the Svelte frontend are aligned with the Flask backend's routes.
- Test integration endpoints locally before deploying.

## Tests

- Write tests only for critical user workflows and essential integration points between the Svelte frontend and the Python backend.
- Do not introduce tests for trivial UI elements or performance metrics initially.
- Run the complete test suite only when explicitly instructed.

### Running the Test Suites

If tests are explicitly requested:
- **Frontend Tests:**
  If using a Svelte testing framework, run:
  ```shell
  npm run test
  ```
- **Backend Tests:**
  Ensure the Python virtual environment is activated, navigate to the Flask project folder, and run:
  ```shell
  pytest
  ```

Ensure to always utilize appropriate browsers or device emulators for testing specific frontend functionality.

---

# Project: Music Streaming Application

**Project Goal:** Develop a web-based music streaming application where users upload their own audio files, which are processed by the backend into segmented formats (HLS/DASH) for playback.

**Target Platform (Initial):** Web app using **Svelte + Tailwind CSS**.

**Current Backend State (v0.2.0 - Monorepo Structure):**

*   **Location:** Resides in the `/backend` directory. Fully functional and tested.
*   **Technology:** Flask, SQLAlchemy, Celery, Mutagen, FFmpeg integration.
*   **Database:** Configurable (PostgreSQL/SQLite), defaults to `backend/app_data.db`.
*   **Authentication:** JWT-based (`/api/auth/`). Requires `Authorization: Bearer <token>` header for protected routes.
*   **Key Functionality:**
    *   User registration/login.
    *   Audio file uploads (`POST /api/tracks/upload`) with metadata (`title`, `artist`, `album`, `track_number`, `output_format` ['HLS'/'DASH']). Triggers background processing.
    *   Background processing extracts metadata, generates HLS/DASH segments, updates track `status` (`PENDING`, `PROCESSING`, `READY`, `ERROR`) and `duration_ms`.
    *   API to list/get tracks (`/api/tracks`), query status (`/api/tracks/<id>/status`), update metadata (`PUT /api/tracks/<id>`), delete tracks (`DELETE /api/tracks/<id>`).
    *   API for playlist management (`/api/playlists`).
    *   Locally processed files generate a `manifest_url` relative to `LOCAL_STORAGE_URL_BASE` (e.g., `/processed/<user_id>/<track_id>/manifest.[m3u8|mpd]`).
*   **Development Server:** Backend runs via `flask run` (requires `FLASK_ENV=development FLASK_DEBUG=1`). Serves processed media at `/processed/` for development **only**.
*   **Production Note:** In production, a proper web server (Nginx/Caddy) must serve the files from the configured `LOCAL_STORAGE_OUTPUT_DIR` at the `LOCAL_STORAGE_URL_BASE` path.

**Plan & Instructions for Frontend Agent:**

**Immediate Goal:** Set up and develop the initial Svelte + Tailwind CSS web application within the `/frontend` directory.

**Core Frontend Requirements:**

1.  **Project Setup:**
    *   Initialize a new Svelte (or SvelteKit) project with Tailwind CSS inside the `/frontend` directory.
    *   Configure necessary development environment for Svelte (Node.js, npm, etc).
2.  **Authentication Flow:**
    *   Create Login and Registration pages/components.
    *   Implement API calls to `/api/auth/login` and `/api/auth/register` on the backend (running at `http://<your-dev-ip>:5000`).
    *   Securely store the received JWT token (e.g., localStorage or sessionStorage).
    *   Implement logic to add the `Authorization: Bearer <token>` header to subsequent API requests.
    *   Implement Logout (clear stored token, navigate to login).
3.  **Track List & Status:**
    *   Create a page/component to display the user's tracks fetched from `GET /api/tracks` (initially filter for `status=READY` for playback).
    *   Display core track metadata (title, artist, album).
    *   *Optional (Deferred):* Display tracks with other statuses and implement polling of `/api/tracks/<id>/status` to update UI for processing tracks.
4.  **Audio Playback:**
    *   When a user selects a `READY` track:
        *   Retrieve its `manifest_url` and `manifest_type`.
        *   Construct the full playback URL (e.g., `http://<your-dev-ip>:5000` + `manifest_url`).
        *   Integrate a web audio player (e.g., hls.js for HLS, dash.js for DASH) for playback in the browser.
5.  **File Upload (Potentially Deferred/Simplified):**
    *   **Challenge:** Direct file system access and multipart uploads from the browser can be complex.
    *   **Initial Simplification (Optional):** Could initially defer direct upload from web and focus on playback of tracks uploaded via `curl` or a future admin UI.
    *   **If Implementing:**
        *   Use a file input to select an audio file.
        *   Create a form UI to collect `title`, `artist`, `album`, `track_number`, `output_format`.
        *   Use the browser's `fetch` or `axios` to construct and send the `multipart/form-data` request to `POST /api/tracks/upload` with the auth token.
6.  **Playlist Management (Lower Priority):** Implement pages/components for viewing playlists and their tracks (`GET /api/playlists`, `GET /api/playlists/<id>`) after basic track playback is working. CRUD operations for playlists can follow.

**Key Backend Info for Frontend:**

*   **API Base URL (Development):** `http://<YOUR_LOCAL_IP>:5000` (Replace `<YOUR_LOCAL_IP>` with the actual IP address of the machine running the Flask backend, accessible from your browser or device on the same network). **Do not use `localhost` or `127.0.0.1` from a mobile device/emulator.**
*   **API Prefix:** `/api`
*   **Authentication:** `Authorization: Bearer <JWT_TOKEN>` header.
*   **Playback URL Base (Development):** `http://<YOUR_LOCAL_IP>:5000` (Manifest URLs returned by API like `/processed/1/6/manifest.m3u8` need this prepended).

**Initial Focus:**

1.  Setup Svelte + Tailwind project.
2.  Implement Auth pages and API calls.
3.  Implement Track list display (for `READY` tracks).
4.  Research and integrate a suitable web audio player for HLS/DASH.
5.  Achieve basic playback.
6.  *Then* tackle upload and playlist features.