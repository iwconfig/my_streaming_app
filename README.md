# Music Streaming Application

A web application for streaming music with HLS/DASH support.

## Project Structure

```
./
├── backend/                  # Flask backend application
│   ├── app/                  # Main application package
│   ├── data/                 # Data storage directory
│   │   ├── temp_uploads/     # Temporary storage for uploads
│   │   └── processed_audio/  # Processed audio files
│   ├── migrations/           # Database migrations
│   ├── tests/                # Test suite
│   ├── .env                  # Backend environment variables
│   ├── .flaskenv             # Flask configuration
│   ├── celery_app.py         # Celery worker configuration
│   ├── config.py             # Application configuration
│   ├── conftest.py           # Test configuration
│   └── run.py                # Application entry point
├── frontend/                 # Frontend application (to be implemented)
├── CHANGELOG.md              # Project changelog
├── LICENSE                   # Project license
└── README.md                 # This file

```

## Setup

### Backend

1. Create and activate a Python virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment:
   - Copy `.env.example` to `.env` and update values
   - Copy `.flaskenv.example` to `.flaskenv` and update values

4. Initialize database:
   ```bash
   flask db upgrade
   ```

5. Run the development server:
   ```bash
   flask run
   ```

6. In a separate terminal, run the Celery worker:
   ```bash
   celery -A celery_app.celery worker --loglevel=info
   ```

### Frontend

To be implemented.

## Development

- Backend API runs at `http://localhost:5000`
- API documentation available at `http://localhost:5000/api/docs`
- Frontend development server will run at `http://localhost:3000`

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the LICENSE file for details.