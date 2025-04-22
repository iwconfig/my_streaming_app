from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Playlist, Track, playlist_tracks
from app.schemas import (
    PlaylistSchema, PlaylistCreateSchema, PlaylistUpdateSchema, PlaylistTrackSchema, PlaylistTrackOrderSchema, TrackSchema
)
from app.extensions import db
from marshmallow import ValidationError
# from sqlalchemy.orm import joinedload # To eager load tracks efficiently
from sqlalchemy.orm import subqueryload
from sqlalchemy import delete, insert

bp = Blueprint('playlists', __name__)
playlist_schema = PlaylistSchema()
playlists_schema = PlaylistSchema(many=True, exclude=("tracks",)) # Exclude tracks for list view
playlist_create_schema = PlaylistCreateSchema()
playlist_update_schema = PlaylistUpdateSchema()
playlist_track_schema = PlaylistTrackSchema()
playlist_track_order_schema = PlaylistTrackOrderSchema()
track_schema = TrackSchema() # For returning tracks within a playlist


@bp.route('', methods=['POST'])
@jwt_required()
def create_playlist():
    current_user_id = int(get_jwt_identity())
    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input data provided"}), 400

    try:
        data = playlist_create_schema.load(json_data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    new_playlist = Playlist(
        user_id=current_user_id,
        name=data['name'],
        description=data.get('description')
    )

    try:
        db.session.add(new_playlist)
        db.session.commit()
        # Return the created playlist (without tracks initially)
        return jsonify(PlaylistSchema(exclude=("tracks",)).dump(new_playlist)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Could not create playlist", "error": str(e)}), 500

@bp.route('', methods=['GET'])
@jwt_required()
def get_playlists():
    current_user_id = int(get_jwt_identity())
    user_playlists = Playlist.query.filter_by(user_id=current_user_id).order_by(Playlist.name).all()
    # Use schema that excludes tracks for efficiency
    return jsonify(playlists_schema.dump(user_playlists)), 200

@bp.route('/<int:playlist_id>', methods=['GET'])
@jwt_required()
def get_playlist_details(playlist_id):
    current_user_id = int(get_jwt_identity())
    # Eager load tracks using joinedload and order them
    playlist = Playlist.query.options(
        # joinedload(Playlist.tracks) # This tells SQLAlchemy to fetch tracks in the same query
        subqueryload(Playlist.tracks)
    ).filter_by(
        id=playlist_id, user_id=current_user_id
    ).first()

    if not playlist:
        return jsonify({"message": "Playlist not found or access denied"}), 404

    # The PlaylistSchema includes nested TrackSchema, so tracks will be serialized
    # The relationship already includes ordering based on playlist_tracks.c.track_order
    return jsonify(playlist_schema.dump(playlist)), 200

@bp.route('/<int:playlist_id>', methods=['PUT'])
@jwt_required()
def update_playlist(playlist_id):
    current_user_id = int(get_jwt_identity())
    playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user_id).first()
    if not playlist:
        return jsonify({"message": "Playlist not found or access denied"}), 404

    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input data provided"}), 400

    try:
        data = playlist_update_schema.load(json_data, partial=True)
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Update fields if they are provided
    if 'name' in data:
        playlist.name = data['name']
    if 'description' in data:
        playlist.description = data['description']

    try:
        db.session.commit()
        # Return updated playlist (without tracks for consistency with create/list)
        return jsonify(PlaylistSchema(exclude=("tracks",)).dump(playlist)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Could not update playlist", "error": str(e)}), 500

@bp.route('/<int:playlist_id>', methods=['DELETE'])
@jwt_required()
def delete_playlist(playlist_id):
    current_user_id = int(get_jwt_identity())
    playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user_id).first()
    if not playlist:
        return jsonify({"message": "Playlist not found or access denied"}), 404

    try:
        # Relationship cascade should handle deleting entries from playlist_tracks
        db.session.delete(playlist)
        db.session.commit()
        return jsonify({"message": "Playlist deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Could not delete playlist", "error": str(e)}), 500

# --- Playlist Track Management ---

@bp.route('/<int:playlist_id>/tracks', methods=['POST'])
@jwt_required()
def add_track_to_playlist(playlist_id):
    current_user_id = int(get_jwt_identity())
    playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user_id).first()
    if not playlist:
        return jsonify({"message": "Playlist not found or access denied"}), 404

    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input data provided"}), 400

    try:
        data = playlist_track_schema.load(json_data)
        track_id = data['track_id']
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Verify the track exists and belongs to the user
    track = Track.query.filter_by(id=track_id, user_id=current_user_id).first()
    if not track:
        return jsonify({"message": "Track not found or access denied"}), 404

    # Check if track is already in the playlist (working with the list directly)
    # playlist.tracks directly gives the list of Track objects
    if any(t.id == track_id for t in playlist.tracks):
         return jsonify({"message": "Track already in playlist"}), 409

    # Determine the order for the new track (append to the end)
    # Use len() on the list
    current_track_count = len(playlist.tracks)
    new_order = current_track_count # 0-based index for the next item

    # Manually insert into the association table
    try:
        stmt = insert(playlist_tracks).values(
            playlist_id=playlist.id,
            track_id=track.id,
            track_order=new_order
        )
        db.session.execute(stmt)
        db.session.commit()
        # You could return the updated playlist details or just a success message
        return jsonify({"message": "Track added to playlist"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Could not add track to playlist", "error": str(e)}), 500


@bp.route('/<int:playlist_id>/tracks/<int:track_id>', methods=['DELETE'])
@jwt_required()
def remove_track_from_playlist(playlist_id, track_id):
    current_user_id = int(get_jwt_identity())

    # Verify playlist exists and belongs to user
    playlist_exists = db.session.query(Playlist.id).filter_by(id=playlist_id, user_id=current_user_id).first() is not None
    if not playlist_exists:
        return jsonify({"message": "Playlist not found or access denied"}), 404

    # Directly delete from the association table
    try:
        stmt = delete(playlist_tracks).where(
            (playlist_tracks.c.playlist_id == playlist_id) &
            (playlist_tracks.c.track_id == track_id)
        )
        result = db.session.execute(stmt)

        # Check if any row was actually deleted
        if result.rowcount == 0:
            return jsonify({"message": "Track not found in this playlist"}), 404

        # Optional: Re-order remaining tracks if necessary (e.g., fill gaps)
        # This can be complex. A simpler approach is to let gaps exist or re-order on fetch/update.
        # For now, we just remove. Re-ordering can be a separate endpoint.

        db.session.commit()
        return jsonify({"message": "Track removed from playlist"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Could not remove track from playlist", "error": str(e)}), 500


@bp.route('/<int:playlist_id>/tracks/order', methods=['PUT'])
@jwt_required()
def reorder_playlist_tracks(playlist_id):
    current_user_id = int(get_jwt_identity())
    playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user_id).first()
    if not playlist:
        return jsonify({"message": "Playlist not found or access denied"}), 404

    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input data provided"}), 400

    try:
        data = playlist_track_order_schema.load(json_data)
        ordered_track_ids = data['track_ids']
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Get current tracks in the playlist to verify IDs are valid
    # Use a set for efficient lookup
    current_track_ids = {track.id for track in playlist.tracks}

    if set(ordered_track_ids) != current_track_ids:
        return jsonify({"message": "Provided track IDs do not match the tracks currently in the playlist"}), 400

    # Update the order in the association table
    try:
        with db.session.begin_nested(): # Use nested transaction for updating multiple rows
            for index, track_id in enumerate(ordered_track_ids):
                # Update the track_order for each entry in the association table
                stmt = db.update(playlist_tracks).where(
                    (playlist_tracks.c.playlist_id == playlist_id) &
                    (playlist_tracks.c.track_id == track_id)
                ).values(track_order=index)
                db.session.execute(stmt)
        db.session.commit() # Commit the main transaction
        return jsonify({"message": "Playlist order updated"}), 200
    except Exception as e:
        db.session.rollback() # Rollback both nested and main transaction on error
        return jsonify({"message": "Could not update playlist order", "error": str(e)}), 500
