import pytest
import os
from app import create_app, db as _db # Rename db to avoid pytest fixture conflict
from app.models import User, Track, Playlist, playlist_tracks # Import models for direct use in tests
from app.extensions import bcrypt # Import bcrypt for direct password setting in fixtures
import tempfile # For creating temporary directories in tests
import shutil # For cleaning up directories

# Define test defaults easily
TEST_DEFAULTS = {
    'TESTING': True,
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'SECRET_KEY': 'test-secret-key',
    'JWT_SECRET_KEY': 'test-jwt-secret-key',
    'BCRYPT_LOG_ROUNDS': 4,
    # --- ADD TEST DEFAULTS FOR MISSING CONFIGS ---
    'CELERY_BROKER_URL': 'memory://', # Use in-memory broker for tests (no redis needed)
    'CELERY_RESULT_BACKEND': 'cache+memory://', # Use in-memory cache backend
    'CELERY_TASK_ALWAYS_EAGER': True, # IMPORTANT: Execute tasks synchronously in tests
    'CELERY_IMPORTS': ('app.tasks',),
    # Use pytest's tmp_path fixture for file paths if possible, or define static ones
    # Note: tmp_path is function-scoped, app is session-scoped. Need a different approach
    # Let's use static relative paths for simplicity, assuming tests run from project root
    'UPLOAD_TEMP_DIR': './test_temp_uploads',
    'LOCAL_STORAGE_OUTPUT_DIR': './test_processed_audio',
    'LOCAL_STORAGE_URL_BASE': '/processed_test/',
    'FFMPEG_PATH': 'ffmpeg', # Assume available for task tests (or mock)
    'FFPROBE_PATH': 'ffprobe',# Assume available for task tests (or mock)
    'FFMPEG_DEFAULT_AUDIO_CODEC': 'aac',
    'FFMPEG_DEFAULT_AUDIO_BITRATE': '128k', # Use lower bitrate for faster tests
    'FFMPEG_DEFAULT_SEGMENT_DURATION': '2', # Use shorter segments for faster tests
    'FFMPEG_ALLOWED_FORMATS': ['HLS', 'DASH'],
    'UPLOAD_PLUGIN': 'local',
    'PROCESSING_ENABLED': True, # Usually True for testing processing logic
    'FFMPEG_ENABLED': True, # Usually True for testing processing logic
}

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    # Use in-memory SQLite for tests by default
    test_db_url = 'sqlite:///:memory:'
    test_config = TEST_DEFAULTS.copy() # Start with defaults
    test_config['SQLALCHEMY_DATABASE_URI'] = test_db_url # Override DB URI

    # Create directories needed for this test session
    os.makedirs(test_config['UPLOAD_TEMP_DIR'], exist_ok=True)
    os.makedirs(test_config['LOCAL_STORAGE_OUTPUT_DIR'], exist_ok=True)

    # Create the app instance using the combined test config
    app_instance = create_app(config_class=type('TestConfig', (object,), test_config))

    with app_instance.app_context():
        _db.create_all() # Create tables once per session
        yield app_instance # provide the app object to the tests
        _db.drop_all() # Drop tables once per session

    # Cleanup directories created for the session
    shutil.rmtree(test_config['UPLOAD_TEMP_DIR'], ignore_errors=True)
    shutil.rmtree(test_config['LOCAL_STORAGE_OUTPUT_DIR'], ignore_errors=True)

@pytest.fixture(scope='function')
def db(app):
    """Function-scoped test database."""
    with app.app_context():
        _db.create_all()
    yield _db
    with app.app_context():
         # Rollback any potentially failed transactions before removing
        try:
             _db.session.rollback()
        except Exception:
             pass # Ignore errors during rollback if session is weird
        finally:
             _db.session.remove()
        _db.drop_all() # drop_all should work fine on :memory:

@pytest.fixture(scope='function')
def client(app, db): # Ensure db fixture runs before client fixture
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app, db): # Ensure db fixture runs before runner fixture
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()

# --- Helper Fixtures ---

@pytest.fixture(scope='function')
def add_user(db):
    """Helper fixture to add a user directly to the DB."""
    def _add_user(username, email, password):
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user
    return _add_user

@pytest.fixture(scope='function')
def auth_tokens(client, add_user):
    """Fixture to register/login users and return their tokens and IDs."""
    tokens = {}
    user_ids = {}

    # User A
    user_a = add_user("user_a", "a@test.com", "password_a")
    resp_a = client.post('/api/auth/login', json={
        "username": "user_a", "password": "password_a"
    })
    assert resp_a.status_code == 200
    tokens['user_a'] = resp_a.json['access_token']
    user_ids['user_a'] = user_a.id

    # User B
    user_b = add_user("user_b", "b@test.com", "password_b")
    resp_b = client.post('/api/auth/login', json={
        "username": "user_b", "password": "password_b"
    })
    assert resp_b.status_code == 200
    tokens['user_b'] = resp_b.json['access_token']
    user_ids['user_b'] = user_b.id

    return {'tokens': tokens, 'ids': user_ids}


@pytest.fixture(scope='function')
def add_track(db):
    """Helper fixture to add a track directly to the DB."""
    def _add_track(user_id, title, manifest_url="http://example.com/test.m3u8", manifest_type="HLS", artist=None, album=None):
        track = Track(
            user_id=user_id,
            title=title,
            manifest_url=manifest_url,
            manifest_type=manifest_type,
            artist=artist,
            album=album
        )
        db.session.add(track)
        db.session.commit()
        return track
    return _add_track

@pytest.fixture(scope='function')
def add_playlist(db):
    """Helper fixture to add a playlist directly to the DB."""
    def _add_playlist(user_id, name, description=None):
        playlist = Playlist(
            user_id=user_id,
            name=name,
            description=description
        )
        db.session.add(playlist)
        db.session.commit()
        return playlist
    return _add_playlist

@pytest.fixture(scope='function')
def add_track_to_playlist_db(db):
    """Helper fixture to add a track to a playlist directly in DB."""
    def _add(playlist_id, track_id, order):
         stmt = _db.insert(playlist_tracks).values(
             playlist_id=playlist_id,
             track_id=track_id,
             track_order=order
         )
         db.session.execute(stmt)
         db.session.commit()
    return _add
