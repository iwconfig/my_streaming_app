import pytest
# Import models needed for assertions and type checks
from app.models import Track, TrackStatus, ManifestType # Added TrackStatus
from unittest.mock import patch # For mocking celery .delay
import os # For path checks

# --- Upload Tests ---

# Corrected patch target
@patch('app.tasks.process_audio_task.delay')
def test_upload_track_success(mock_delay, client, auth_tokens, tmp_path): # Renamed test
    """Test successful track upload request.""" # Updated docstring
    token = auth_tokens['tokens']['user_a']
    user_id = auth_tokens['ids']['user_a']
    dummy_file = tmp_path / "test_audio.mp3"
    dummy_file.write_text("dummy audio content")
    # Combine form data and file into data dict
    form_data_with_file = {
        'title': 'Uploaded Song',
        'artist': 'Uploader',
        'output_format': 'HLS',
        'audio_file': dummy_file.open('rb')
    }
    response = client.post('/api/tracks/upload',
                           headers={'Authorization': f'Bearer {token}'},
                           data=form_data_with_file, # Pass combined dict
                           content_type='multipart/form-data',
                           buffered=True
                           # Removed files=...
                           )
    form_data_with_file['audio_file'].close() # Close file handle

    assert response.status_code == 202
    json_data = response.json
    assert json_data['title'] == form_data_with_file['title']
    assert json_data['artist'] == form_data_with_file['artist']
    assert json_data['status'] == 'PENDING'
    assert json_data['user_id'] == user_id
    track_id = json_data['id']
    mock_delay.assert_called_once()
    call_args = mock_delay.call_args[1]
    assert call_args['track_id'] == track_id
    assert call_args['output_format'] == 'HLS'
    temp_path_arg = call_args['temp_input_path']
    # Corrected path comparison
    expected_dir = os.path.abspath(client.application.config['UPLOAD_TEMP_DIR'])
    actual_dir = os.path.abspath(os.path.dirname(temp_path_arg))
    assert actual_dir == expected_dir
    assert temp_path_arg.endswith('.mp3')

# Corrected patch target
@patch('app.tasks.process_audio_task.delay')
def test_upload_track_no_file(mock_delay, client, auth_tokens):
    """Test upload request missing the audio file."""
    token = auth_tokens['tokens']['user_a']
    form_data = {'title': 'No File Song'}
    response = client.post('/api/tracks/upload',
                           headers={'Authorization': f'Bearer {token}'},
                           data=form_data,
                           content_type='multipart/form-data')
    assert response.status_code == 400
    assert b"Missing 'audio_file' part" in response.data
    mock_delay.assert_not_called()

# Corrected patch target
@patch('app.tasks.process_audio_task.delay')
def test_upload_track_missing_metadata(mock_delay, client, auth_tokens, tmp_path):
    """Test upload request missing required metadata (title)."""
    token = auth_tokens['tokens']['user_a']
    dummy_file = tmp_path / "test.mp3"
    dummy_file.write_text("dummy")
    # Combine form data and file
    form_data_with_file = {
        'artist': 'No Title', # Missing title
        'audio_file': dummy_file.open('rb')
    }
    response = client.post('/api/tracks/upload',
                           headers={'Authorization': f'Bearer {token}'},
                           data=form_data_with_file, # Pass combined dict
                           content_type='multipart/form-data',
                           buffered=True
                           # Removed files=...
                           )
    form_data_with_file['audio_file'].close() # Close file handle

    assert response.status_code == 400
    assert b"validation_errors" in response.data
    # Access nested error
    assert b"title" in response.data
    assert b"Missing data for required field" in response.data
    mock_delay.assert_not_called()

# Corrected patch target
@patch('app.tasks.process_audio_task.delay')
def test_upload_track_invalid_format(mock_delay, client, auth_tokens, tmp_path):
    """Test upload request with an invalid output_format."""
    token = auth_tokens['tokens']['user_a']
    dummy_file = tmp_path / "test.mp3"
    dummy_file.write_text("dummy")
    # Combine form data and file
    form_data_with_file = {
        'title': 'Bad Format',
        'output_format': 'MP3', # Invalid format
        'audio_file': dummy_file.open('rb')
    }
    response = client.post('/api/tracks/upload',
                           headers={'Authorization': f'Bearer {token}'},
                           data=form_data_with_file, # Pass combined dict
                           content_type='multipart/form-data',
                           buffered=True
                           # Removed files=...
                           )
    form_data_with_file['audio_file'].close() # Close file handle

    assert response.status_code == 400
    assert b"Unsupported output_format" in response.data or b"output_format must be HLS or DASH" in response.data
    mock_delay.assert_not_called()

# --- Test for Status Endpoint ---
# Removed 'self' from signature
def test_get_track_status(client, auth_tokens, add_track):
     """Test getting just the status of a track."""
     user_id = auth_tokens['ids']['user_a']
     token = auth_tokens['tokens']['user_a']
     track = add_track(user_id=user_id, title="Status Check Track")
     response = client.get(f'/api/tracks/{track.id}/status', headers={'Authorization': f'Bearer {token}'})
     assert response.status_code == 200
     json_data = response.json
     assert json_data['id'] == track.id
     # Use imported TrackStatus Enum
     assert json_data['status'] == TrackStatus.PENDING.value
     assert json_data['error_message'] is None
     assert "title" not in json_data

# --- Add Track By URL Tests --- #

def test_add_track_by_url_success(client, auth_tokens): # Renamed
    """Test successfully adding a track by URL."""
    token = auth_tokens['tokens']['user_a']
    user_id = auth_tokens['ids']['user_a']
    track_data = {
        "title": "Test Song Added By URL", "artist": "Artist URL", "album": "Album URL",
        "manifest_url": "http://example.com/track_url.m3u8", "manifest_type": "HLS",
        "duration_ms": 180000
    }
    response = client.post('/api/tracks/add_by_url', json=track_data, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 201
    json_data = response.json
    assert json_data['title'] == track_data['title']
    assert json_data['manifest_url'] == track_data['manifest_url']
    assert json_data['user_id'] == user_id
    assert json_data['status'] == TrackStatus.READY.value

def test_add_track_by_url_unauthorized(client):
    """Test adding track by URL without auth token."""
    track_data = {
        "title": "Unauthorized Song", "manifest_url": "http://example.com/unauth.mpd", "manifest_type": "DASH"
    }
    response = client.post('/api/tracks/add_by_url', json=track_data)
    assert response.status_code == 401

def test_add_track_by_url_missing_required_fields(client, auth_tokens):
    """Test adding track by URL with missing required fields."""
    token = auth_tokens['tokens']['user_a']
    track_data = {"artist": "Incomplete Artist"}
    response = client.post('/api/tracks/add_by_url', json=track_data, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 400
    json_data = response.json
    assert 'validation_errors' in json_data
    # Corrected nested check
    assert 'title' in json_data['validation_errors']
    assert 'manifest_url' in json_data['validation_errors']
    assert 'manifest_type' in json_data['validation_errors']

def test_add_track_by_url_invalid_manifest_type(client, auth_tokens):
    """Test adding track by URL with invalid manifest type."""
    token = auth_tokens['tokens']['user_a']
    track_data = {
        "title": "Invalid Type Song", "manifest_url": "http://example.com/invalid.m3u8",
        "manifest_type": "MP3"
    }
    response = client.post('/api/tracks/add_by_url', json=track_data, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 400
    assert b"manifest_type" in response.data
    assert b"Must be one of: HLS, DASH" in response.data

# --- Get Tracks Tests (No changes needed) ---
def test_get_tracks_empty(client, auth_tokens):
    token = auth_tokens['tokens']['user_a']
    response = client.get('/api/tracks', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200; assert response.json == []
def test_get_tracks_success(client, auth_tokens, add_track):
    user_a_id, user_b_id = auth_tokens['ids']['user_a'], auth_tokens['ids']['user_b']
    token_a = auth_tokens['tokens']['user_a']
    t1 = add_track(user_a_id, "User A Song 1"); t2 = add_track(user_a_id, "User A Song 2"); t3 = add_track(user_b_id, "User B Song 1")
    response = client.get('/api/tracks', headers={'Authorization': f'Bearer {token_a}'})
    assert response.status_code == 200; json_data = response.json; assert len(json_data) == 2
    ids = {t['id'] for t in json_data}; assert t1.id in ids; assert t2.id in ids; assert t3.id not in ids
def test_get_specific_track_success(client, auth_tokens, add_track):
    user_id, token = auth_tokens['ids']['user_a'], auth_tokens['tokens']['user_a']
    track = add_track(user_id, "Specific Song")
    response = client.get(f'/api/tracks/{track.id}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200; json_data = response.json
    assert json_data['id'] == track.id; assert json_data['title'] == "Specific Song"; assert json_data['user_id'] == user_id
def test_get_specific_track_not_found(client, auth_tokens):
    token = auth_tokens['tokens']['user_a']
    response = client.get('/api/tracks/999', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 404; assert b"Track not found" in response.data
def test_get_specific_track_wrong_user(client, auth_tokens, add_track):
    user_a_id, user_b_id = auth_tokens['ids']['user_a'], auth_tokens['ids']['user_b']
    token_b = auth_tokens['tokens']['user_b']; track_a = add_track(user_a_id, "User A's Secret Song")
    response = client.get(f'/api/tracks/{track_a.id}', headers={'Authorization': f'Bearer {token_b}'})
    assert response.status_code == 404; assert b"Track not found" in response.data

# --- Update Track Tests (No changes needed) ---
def test_update_track_success(client, db, auth_tokens, add_track):
    user_id, token = auth_tokens['ids']['user_a'], auth_tokens['tokens']['user_a']
    track = add_track(user_id, "Original Title", artist="Original Artist")
    update_data = {"title": "Updated Title", "artist": "Updated Artist"}
    response = client.put(f'/api/tracks/{track.id}', json=update_data, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200; json_data = response.json
    assert json_data['title'] == update_data['title']; assert json_data['artist'] == update_data['artist']
    db_track = db.session.get(Track, track.id)
    assert db_track.title == update_data['title']; assert db_track.artist == update_data['artist']
def test_update_track_partial(client, auth_tokens, add_track):
    user_id, token = auth_tokens['ids']['user_a'], auth_tokens['tokens']['user_a']
    track = add_track(user_id, "Partial Update", artist="Keep This", album="Keep This Too")
    update_data = {"title": "Partial Update Done"}
    response = client.put(f'/api/tracks/{track.id}', json=update_data, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200; json_data = response.json
    assert json_data['title'] == update_data['title']; assert json_data['artist'] == "Keep This"; assert json_data['album'] == "Keep This Too"
def test_update_track_not_found(client, auth_tokens):
    token = auth_tokens['tokens']['user_a']; update_data = {"title": "Won't Work"}
    response = client.put('/api/tracks/999', json=update_data, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 404
def test_update_track_wrong_user(client, auth_tokens, add_track):
    user_a_id, user_b_id = auth_tokens['ids']['user_a'], auth_tokens['ids']['user_b']
    token_b = auth_tokens['tokens']['user_b']; track_a = add_track(user_a_id, "User A's Song")
    update_data = {"title": "Hacked!"}
    response = client.put(f'/api/tracks/{track_a.id}', json=update_data, headers={'Authorization': f'Bearer {token_b}'})
    assert response.status_code == 404

# --- Delete Track Tests (No changes needed) ---
def test_delete_track_success(client, db, auth_tokens, add_track):
    user_id, token = auth_tokens['ids']['user_a'], auth_tokens['tokens']['user_a']
    track = add_track(user_id, "To Be Deleted"); track_id = track.id
    response = client.delete(f'/api/tracks/{track_id}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200; assert b"Track deleted successfully" in response.data
    db_track = db.session.get(Track, track_id); assert db_track is None
def test_delete_track_not_found(client, auth_tokens):
    token = auth_tokens['tokens']['user_a']
    response = client.delete('/api/tracks/999', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 404
def test_delete_track_wrong_user(client, db, auth_tokens, add_track):
    user_a_id, user_b_id = auth_tokens['ids']['user_a'], auth_tokens['ids']['user_b']
    token_b = auth_tokens['tokens']['user_b']; track_a = add_track(user_a_id, "User A's Song")
    response = client.delete(f'/api/tracks/{track_a.id}', headers={'Authorization': f'Bearer {token_b}'})
    assert response.status_code == 404
    db_track_a = db.session.get(Track, track_a.id); assert db_track_a is not None
