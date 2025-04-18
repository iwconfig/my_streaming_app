import pytest
from app.models import Track, ManifestType

# --- Add Track Tests ---

def test_add_track_success(client, auth_tokens):
    """Test successfully adding a track."""
    token = auth_tokens['tokens']['user_a']
    user_id = auth_tokens['ids']['user_a']
    track_data = {
        "title": "Test Song 1",
        "artist": "Artist A",
        "album": "Album X",
        "manifest_url": "http://example.com/track1.m3u8",
        "manifest_type": "HLS",
        "duration_ms": 180000
    }
    response = client.post('/api/tracks', json=track_data, headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 201
    json_data = response.json
    assert json_data['title'] == track_data['title']
    assert json_data['artist'] == track_data['artist']
    assert json_data['album'] == track_data['album']
    assert json_data['manifest_url'] == track_data['manifest_url']
    assert json_data['manifest_type'] == track_data['manifest_type']
    assert json_data['duration_ms'] == track_data['duration_ms']
    assert json_data['user_id'] == user_id
    assert 'id' in json_data
    assert 'added_at' in json_data

    # Check database
    track = Track.query.filter_by(id=json_data['id']).first()
    assert track is not None
    assert track.title == track_data['title']
    assert track.user_id == user_id
    assert track.manifest_type == ManifestType.HLS # Check Enum value

def test_add_track_unauthorized(client):
    """Test adding track without auth token."""
    track_data = {
        "title": "Unauthorized Song",
        "manifest_url": "http://example.com/unauth.mpd",
        "manifest_type": "DASH"
    }
    response = client.post('/api/tracks', json=track_data)
    assert response.status_code == 401

def test_add_track_missing_required_fields(client, auth_tokens):
    """Test adding track with missing required fields."""
    token = auth_tokens['tokens']['user_a']
    # Missing title, manifest_url, manifest_type
    track_data = {"artist": "Incomplete Artist"}
    response = client.post('/api/tracks', json=track_data, headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 400
    json_data = response.json
    assert 'title' in json_data # Marshmallow validation errors
    assert 'manifest_url' in json_data

def test_add_track_invalid_manifest_type(client, auth_tokens):
    """Test adding track with invalid manifest type."""
    token = auth_tokens['tokens']['user_a']
    track_data = {
        "title": "Invalid Type Song",
        "manifest_url": "http://example.com/invalid.m3u8",
        "manifest_type": "MP3" # Invalid enum value
    }
    response = client.post('/api/tracks', json=track_data, headers={
        'Authorization': f'Bearer {token}'
    })
    assert response.status_code == 400
    assert b"Must be one of: HLS, DASH" in response.data # Check Marshmallow error

# --- Get Tracks Tests ---

def test_get_tracks_empty(client, auth_tokens):
    """Test getting tracks when none exist for the user."""
    token = auth_tokens['tokens']['user_a']
    response = client.get('/api/tracks', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert response.json == []

def test_get_tracks_success(client, auth_tokens, add_track):
    """Test getting tracks for a user."""
    user_a_id = auth_tokens['ids']['user_a']
    user_b_id = auth_tokens['ids']['user_b']
    token_a = auth_tokens['tokens']['user_a']

    # Add tracks for both users
    track1 = add_track(user_a_id, "User A Song 1")
    track2 = add_track(user_a_id, "User A Song 2")
    track3 = add_track(user_b_id, "User B Song 1")

    response = client.get('/api/tracks', headers={'Authorization': f'Bearer {token_a}'})
    assert response.status_code == 200
    json_data = response.json
    assert len(json_data) == 2
    track_ids = {t['id'] for t in json_data}
    assert track1.id in track_ids
    assert track2.id in track_ids
    assert track3.id not in track_ids # Ensure User B's track isn't returned

def test_get_specific_track_success(client, auth_tokens, add_track):
    """Test getting a specific track successfully."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    track = add_track(user_id, "Specific Song")

    response = client.get(f'/api/tracks/{track.id}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    json_data = response.json
    assert json_data['id'] == track.id
    assert json_data['title'] == "Specific Song"
    assert json_data['user_id'] == user_id

def test_get_specific_track_not_found(client, auth_tokens):
    """Test getting a track that doesn't exist."""
    token = auth_tokens['tokens']['user_a']
    response = client.get('/api/tracks/999', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 404
    assert b"Track not found or access denied" in response.data

def test_get_specific_track_wrong_user(client, auth_tokens, add_track):
    """Test getting a track belonging to another user."""
    user_a_id = auth_tokens['ids']['user_a']
    user_b_id = auth_tokens['ids']['user_b']
    token_b = auth_tokens['tokens']['user_b'] # User B's token
    track_a = add_track(user_a_id, "User A's Secret Song") # Track belongs to User A

    # User B tries to access User A's track
    response = client.get(f'/api/tracks/{track_a.id}', headers={'Authorization': f'Bearer {token_b}'})
    assert response.status_code == 404 # Should be not found for this user
    assert b"Track not found or access denied" in response.data

# --- Update Track Tests ---

def test_update_track_success(client, db, auth_tokens, add_track):
    """Test updating a track successfully."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    track = add_track(user_id, "Original Title", artist="Original Artist")
    update_data = {"title": "Updated Title", "artist": "Updated Artist"}

    response = client.put(f'/api/tracks/{track.id}', json=update_data, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    json_data = response.json
    assert json_data['id'] == track.id
    assert json_data['title'] == update_data['title']
    assert json_data['artist'] == update_data['artist']

    # Verify DB
    db_track = db.session.get(Track, track.id)
    assert db_track.title == update_data['title']
    assert db_track.artist == update_data['artist']

def test_update_track_partial(client, auth_tokens, add_track):
    """Test updating only some fields of a track."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    track = add_track(user_id, "Partial Update", artist="Keep This", album="Keep This Too")
    update_data = {"title": "Partial Update Done"} # Only update title

    response = client.put(f'/api/tracks/{track.id}', json=update_data, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    json_data = response.json
    assert json_data['title'] == update_data['title']
    assert json_data['artist'] == "Keep This" # Verify other fields unchanged
    assert json_data['album'] == "Keep This Too"

def test_update_track_not_found(client, auth_tokens):
    """Test updating a non-existent track."""
    token = auth_tokens['tokens']['user_a']
    update_data = {"title": "Won't Work"}
    response = client.put('/api/tracks/999', json=update_data, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 404

def test_update_track_wrong_user(client, auth_tokens, add_track):
    """Test updating a track belonging to another user."""
    user_a_id = auth_tokens['ids']['user_a']
    user_b_id = auth_tokens['ids']['user_b']
    token_b = auth_tokens['tokens']['user_b']
    track_a = add_track(user_a_id, "User A's Song")
    update_data = {"title": "Hacked!"}

    response = client.put(f'/api/tracks/{track_a.id}', json=update_data, headers={'Authorization': f'Bearer {token_b}'})
    assert response.status_code == 404

# --- Delete Track Tests ---

def test_delete_track_success(client, db, auth_tokens, add_track):
    """Test deleting a track successfully."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    track = add_track(user_id, "To Be Deleted")
    track_id = track.id

    response = client.delete(f'/api/tracks/{track_id}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert b"Track deleted successfully" in response.data

    # Verify DB
    db_track = db.session.get(Track, track_id) # Use db.session.get for primary key lookup
    assert db_track is None

def test_delete_track_not_found(client, auth_tokens):
    """Test deleting a non-existent track."""
    token = auth_tokens['tokens']['user_a']
    response = client.delete('/api/tracks/999', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 404

def test_delete_track_wrong_user(client, db, auth_tokens, add_track):
    """Test deleting a track belonging to another user."""
    user_a_id = auth_tokens['ids']['user_a']
    user_b_id = auth_tokens['ids']['user_b']
    token_b = auth_tokens['tokens']['user_b']
    track_a = add_track(user_a_id, "User A's Song")

    response = client.delete(f'/api/tracks/{track_a.id}', headers={'Authorization': f'Bearer {token_b}'})
    assert response.status_code == 404

    # Verify track A still exists
    db_track_a = db.session.get(Track, track_a.id)
    assert db_track_a is not None
