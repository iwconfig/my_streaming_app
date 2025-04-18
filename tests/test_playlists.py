import pytest
from app.models import Playlist, Track

# --- Playlist CRUD ---

def test_create_playlist_success(client, auth_tokens):
    """Test creating a playlist successfully."""
    token = auth_tokens['tokens']['user_a']
    user_id = auth_tokens['ids']['user_a']
    playlist_data = {"name": "My Test Playlist", "description": "Test Desc"}

    response = client.post('/api/playlists', json=playlist_data, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 201
    json_data = response.json
    assert json_data['name'] == playlist_data['name']
    assert json_data['description'] == playlist_data['description']
    assert json_data['user_id'] == user_id
    assert 'id' in json_data
    assert 'tracks' not in json_data # List view excludes tracks

def test_get_playlists_success(client, auth_tokens, add_playlist):
    """Test getting playlists for a user."""
    user_a_id = auth_tokens['ids']['user_a']
    user_b_id = auth_tokens['ids']['user_b']
    token_a = auth_tokens['tokens']['user_a']

    pl1 = add_playlist(user_a_id, "User A Playlist 1")
    pl2 = add_playlist(user_a_id, "User A Playlist 2")
    pl3 = add_playlist(user_b_id, "User B Playlist 1")

    response = client.get('/api/playlists', headers={'Authorization': f'Bearer {token_a}'})
    assert response.status_code == 200
    json_data = response.json
    assert len(json_data) == 2
    playlist_ids = {p['id'] for p in json_data}
    assert pl1.id in playlist_ids
    assert pl2.id in playlist_ids
    assert pl3.id not in playlist_ids

def test_get_playlist_details_empty(client, auth_tokens, add_playlist):
    """Test getting details of an empty playlist."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    playlist = add_playlist(user_id, "Empty Playlist")

    response = client.get(f'/api/playlists/{playlist.id}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    json_data = response.json
    assert json_data['id'] == playlist.id
    assert json_data['name'] == "Empty Playlist"
    assert json_data['tracks'] == []

def test_update_playlist_success(client, auth_tokens, add_playlist):
    """Test updating playlist metadata."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    playlist = add_playlist(user_id, "Old Name", "Old Desc")
    update_data = {"name": "New Name", "description": "New Desc"}

    response = client.put(f'/api/playlists/{playlist.id}', json=update_data, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    json_data = response.json
    assert json_data['name'] == update_data['name']
    assert json_data['description'] == update_data['description']

def test_delete_playlist_success(client, db, auth_tokens, add_playlist):
    """Test deleting a playlist."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    playlist = add_playlist(user_id, "To Delete")
    playlist_id = playlist.id

    response = client.delete(f'/api/playlists/{playlist_id}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert b"Playlist deleted successfully" in response.data

    # Verify DB
    db_playlist = db.session.get(Playlist, playlist_id)
    assert db_playlist is None

# --- Playlist Track Management ---

def test_add_track_to_playlist_success(client, auth_tokens, add_playlist, add_track):
    """Test adding a track to a playlist."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    playlist = add_playlist(user_id, "Playlist With Track")
    track = add_track(user_id, "Track To Add")

    response = client.post(f'/api/playlists/{playlist.id}/tracks', json={"track_id": track.id}, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 201
    assert b"Track added to playlist" in response.data

    # Verify by getting details
    response_details = client.get(f'/api/playlists/{playlist.id}', headers={'Authorization': f'Bearer {token}'})
    assert response_details.status_code == 200
    json_data = response_details.json
    assert len(json_data['tracks']) == 1
    assert json_data['tracks'][0]['id'] == track.id
    assert json_data['tracks'][0]['title'] == track.title

def test_add_track_to_playlist_duplicate(client, auth_tokens, add_playlist, add_track):
    """Test adding the same track twice."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    playlist = add_playlist(user_id, "Playlist For Dupe")
    track = add_track(user_id, "Dupe Track")

    # Add first time
    client.post(f'/api/playlists/{playlist.id}/tracks', json={"track_id": track.id}, headers={'Authorization': f'Bearer {token}'})

    # Add second time
    response = client.post(f'/api/playlists/{playlist.id}/tracks', json={"track_id": track.id}, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 409
    assert b"Track already in playlist" in response.data

def test_add_track_to_playlist_track_not_found(client, auth_tokens, add_playlist):
    """Test adding a non-existent track."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    playlist = add_playlist(user_id, "Playlist")

    response = client.post(f'/api/playlists/{playlist.id}/tracks', json={"track_id": 999}, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 404
    assert b"Track not found or access denied" in response.data

def test_add_track_to_playlist_wrong_user_track(client, auth_tokens, add_playlist, add_track):
    """Test adding another user's track."""
    user_a_id = auth_tokens['ids']['user_a']
    user_b_id = auth_tokens['ids']['user_b']
    token_a = auth_tokens['tokens']['user_a']
    playlist_a = add_playlist(user_a_id, "User A Playlist")
    track_b = add_track(user_b_id, "User B Track") # Track belongs to User B

    # User A tries to add User B's track to User A's playlist
    response = client.post(f'/api/playlists/{playlist_a.id}/tracks', json={"track_id": track_b.id}, headers={'Authorization': f'Bearer {token_a}'})
    assert response.status_code == 404 # Track not found for User A
    assert b"Track not found or access denied" in response.data

def test_remove_track_from_playlist_success(client, auth_tokens, add_playlist, add_track, add_track_to_playlist_db):
    """Test removing a track from a playlist."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    playlist = add_playlist(user_id, "Playlist To Edit")
    track = add_track(user_id, "Track To Remove")
    add_track_to_playlist_db(playlist.id, track.id, 0) # Add directly to DB for setup

    # Verify it's there first
    response_details = client.get(f'/api/playlists/{playlist.id}', headers={'Authorization': f'Bearer {token}'})
    assert len(response_details.json['tracks']) == 1

    # Remove the track
    response_remove = client.delete(f'/api/playlists/{playlist.id}/tracks/{track.id}', headers={'Authorization': f'Bearer {token}'})
    assert response_remove.status_code == 200
    assert b"Track removed from playlist" in response_remove.data

    # Verify it's gone
    response_details_after = client.get(f'/api/playlists/{playlist.id}', headers={'Authorization': f'Bearer {token}'})
    assert response_details_after.status_code == 200
    assert len(response_details_after.json['tracks']) == 0

def test_remove_track_from_playlist_not_in_list(client, auth_tokens, add_playlist, add_track):
    """Test removing a track that isn't in the playlist."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    playlist = add_playlist(user_id, "Playlist")
    track = add_track(user_id, "Track") # Track exists but not added

    response = client.delete(f'/api/playlists/{playlist.id}/tracks/{track.id}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 404
    assert b"Track not found in this playlist" in response.data

def test_reorder_playlist_tracks_success(client, auth_tokens, add_playlist, add_track, add_track_to_playlist_db):
    """Test reordering tracks in a playlist."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    playlist = add_playlist(user_id, "Reorder Playlist")
    track1 = add_track(user_id, "Track 1")
    track2 = add_track(user_id, "Track 2")
    track3 = add_track(user_id, "Track 3")
    add_track_to_playlist_db(playlist.id, track1.id, 0)
    add_track_to_playlist_db(playlist.id, track2.id, 1)
    add_track_to_playlist_db(playlist.id, track3.id, 2)

    # Define new order
    new_order_ids = [track3.id, track1.id, track2.id]

    response = client.put(f'/api/playlists/{playlist.id}/tracks/order', json={"track_ids": new_order_ids}, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert b"Playlist order updated" in response.data

    # Verify new order
    response_details = client.get(f'/api/playlists/{playlist.id}', headers={'Authorization': f'Bearer {token}'})
    assert response_details.status_code == 200
    ordered_tracks = response_details.json['tracks']
    assert len(ordered_tracks) == 3
    assert ordered_tracks[0]['id'] == track3.id
    assert ordered_tracks[1]['id'] == track1.id
    assert ordered_tracks[2]['id'] == track2.id

def test_reorder_playlist_tracks_id_mismatch(client, auth_tokens, add_playlist, add_track, add_track_to_playlist_db):
    """Test reordering with mismatched track IDs."""
    user_id = auth_tokens['ids']['user_a']
    token = auth_tokens['tokens']['user_a']
    playlist = add_playlist(user_id, "Mismatch Playlist")
    track1 = add_track(user_id, "T1")
    track2 = add_track(user_id, "T2")
    add_track_to_playlist_db(playlist.id, track1.id, 0)
    add_track_to_playlist_db(playlist.id, track2.id, 1)

    # Try to reorder with wrong IDs (e.g., includes a non-existent ID 999)
    new_order_ids = [track2.id, track1.id, 999]

    response = client.put(f'/api/playlists/{playlist.id}/tracks/order', json={"track_ids": new_order_ids}, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 400
    assert b"Provided track IDs do not match the tracks currently in the playlist" in response.data
