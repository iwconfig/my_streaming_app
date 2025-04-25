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
- Always use Svelte Native for building UI components.
- Use modern styling and layouts that adapt beautifully on both iOS and Android.
- Avoid mixing in any non-cross-platform components; all UI should be implemented in Svelte Native.
- Ensure all UI components are responsive and visually appealing on modern devices.

## Build & Run

Run in docker container for all commands. This ensures that the environment is consistent and avoids issues with local dependencies.

Always build and run the app after making any code changes to verify functionality.

### To Build the App

Use the Svelte Native CLI to build the project for each platform. For example:

- **iOS:**
  Build using a modern iOS device as the target (default to an iPhone 14):
  ```shell
  ns build ios --release
  ```
- **Android:**
  Build targeting a modern Android device (default to a Pixel 6):
  ```shell
  ns build android --release
  ```

### To Run the App

Before deployment, ensure a valid simulator/emulator is running. Then, instruct the app to run with the following commands:

- **iOS Simulator:**
  Use the iPhone 14 simulator as the default:
  ```shell
  ns run ios --device "iPhone 14"
  ```
- **Android Emulator:**
  Use the Pixel 6 emulator as the default:
  ```shell
  ns run android --emulator "Pixel_6_API_30"
  ```

Note: Although "Pixel_6_API_30" and "iPhone 14" are given as the default, the actual emulator name must match the configuration in the development environment.

## Backend Integration

- The backend is powered by Python Flask and Python Celery.
- Ensure that any backend work is performed within the project's Python virtual environment; this virtual environment is located at ./venv.
- Activate the virtual environment with:
  ```shell
  source ./venv/bin/activate
  ```
  (On Windows, use `.\venv\Scripts\activate`.)
- Verify that API calls made from the Svelte Native frontend are aligned with the Flask backend's routes.
- Test integration endpoints locally before deploying.

## Tests

- Write tests only for critical user workflows and essential integration points between the Svelte Native frontend and the Python backend.
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

Ensure to always utilize appropriate simulators/emulators for testing specific frontend functionality.

---

# Project: Music Streaming Application

**Project Goal:** Develop a native mobile music streaming application (iOS & Android) where users upload their own audio files, which are processed by the backend into segmented formats (HLS/DASH) for playback.

**Target Platform (Initial):** Native Mobile (iOS/Android) using **Svelte Native** (Svelte + NativeScript).

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

**Immediate Goal:** Set up and develop the initial Svelte Native mobile application within the `/frontend` directory.

**Core Frontend Requirements:**

1.  **Project Setup:**
    *   Initialize a new NativeScript project with the Svelte template inside the `/frontend` directory. (`ns create myApp --svelte`)
    *   Configure necessary development environment for NativeScript (Node.js, NativeScript CLI, platform SDKs - Android Studio/Xcode).
2.  **Authentication Flow:**
    *   Create Login and Registration screens/components.
    *   Implement API calls to `/api/auth/login` and `/api/auth/register` on the backend (running at `http://<your-dev-ip>:5000` - **Note:** Use your machine's actual IP, not `127.0.0.1`, when running on a device/emulator).
    *   Securely store the received JWT token using appropriate NativeScript mechanisms (e.g., `nativescript-secure-storage`).
    *   Implement logic to add the `Authorization: Bearer <token>` header to subsequent API requests.
    *   Implement Logout (clear stored token, navigate to login).
3.  **Track List & Status:**
    *   Create a screen/component to display the user's tracks fetched from `GET /api/tracks` (initially filter for `status=READY` for playback).
    *   Display core track metadata (title, artist, album).
    *   *Optional (Deferred):* Display tracks with other statuses and implement polling of `/api/tracks/<id>/status` to update UI for processing tracks.
4.  **Audio Playback:**
    *   When a user selects a `READY` track:
        *   Retrieve its `manifest_url` and `manifest_type`.
        *   Construct the full playback URL (e.g., `http://<your-dev-ip>:5000` + `manifest_url`).
        *   Integrate a NativeScript audio player plugin capable of handling HLS/DASH streams (e.g., potentially `nativescript-video-player` with modifications, or explore other community audio plugins). **This is a key research area.** Verify plugin compatibility with HLS/DASH on both iOS and Android.
5.  **File Upload (Potentially Deferred/Simplified):**
    *   **Challenge:** Direct file system access and multipart uploads from native mobile can be complex.
    *   **Initial Simplification (Optional):** Could initially defer direct upload from mobile and focus on playback of tracks uploaded via `curl` or a future web UI.
    *   **If Implementing:**
        *   Use a NativeScript file picker plugin (e.g., `nativescript-document-picker` or similar) to select an audio file.
        *   Create a form UI to collect `title`, `artist`, `album`, `track_number`, `output_format`.
        *   Use NativeScript's `Http` module or a background upload plugin (like `nativescript-background-http`) to construct and send the `multipart/form-data` request to `POST /api/tracks/upload` with the auth token. Handle potential background upload complexities.
6.  **Playlist Management (Lower Priority):** Implement screens/components for viewing playlists and their tracks (`GET /api/playlists`, `GET /api/playlists/<id>`) after basic track playback is working. CRUD operations for playlists can follow.

**Key Backend Info for Frontend:**

*   **API Base URL (Development):** `http://<YOUR_LOCAL_IP>:5000` (Replace `<YOUR_LOCAL_IP>` with the actual IP address of the machine running the Flask backend, accessible from your phone/emulator network). **Do not use `localhost` or `127.0.0.1` from a mobile device/emulator.**
*   **API Prefix:** `/api`
*   **Authentication:** `Authorization: Bearer <JWT_TOKEN>` header.
*   **Playback URL Base (Development):** `http://<YOUR_LOCAL_IP>:5000` (Manifest URLs returned by API like `/processed/1/6/manifest.m3u8` need this prepended).

**Initial Focus:**

1.  Setup Svelte Native project.
2.  Implement Auth screens and API calls.
3.  Implement Track list display (for `READY` tracks).
4.  Research and integrate a suitable NativeScript player plugin for HLS/DASH.
5.  Achieve basic playback.
6.  *Then* tackle upload and playlist features.