from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Track, ManifestType
from app.schemas import TrackSchema, TrackLoadSchema, TrackUpdateSchema
from app.extensions import db
from marshmallow import ValidationError

bp = Blueprint('tracks', __name__)
track_schema = TrackSchema()
tracks_schema = TrackSchema(many=True)
track_load_schema = TrackLoadSchema()
track_update_schema = TrackUpdateSchema()

@bp.route('', methods=['POST'])
@jwt_required()
def add_track():
    current_user_id = int(get_jwt_identity())
    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input data provided"}), 400

    try:
        # Validate input data using the load schema
        data = track_load_schema.load(json_data)
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Check if manifest_type is valid (already handled by Marshmallow Enum field)
    # manifest_type_enum = ManifestType[data['manifest_type']] # Convert string back to Enum if needed by model

    new_track = Track(
        user_id=current_user_id,
        title=data['title'],
        artist=data.get('artist'), # Use .get for optional fields
        album=data.get('album'),
        track_number=data.get('track_number'),
        duration_ms=data.get('duration_ms'),
        manifest_url=data['manifest_url'],
        manifest_type=data['manifest_type'] # Marshmallow handles enum conversion
    )

    try:
        db.session.add(new_track)
        db.session.commit()
        return jsonify(track_schema.dump(new_track)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Could not add track", "error": str(e)}), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_tracks():
    current_user_id = int(get_jwt_identity())
    user_tracks = Track.query.filter_by(user_id=current_user_id).order_by(Track.artist, Track.album, Track.track_number, Track.title).all()
    return jsonify(tracks_schema.dump(user_tracks)), 200

@bp.route('/<int:track_id>', methods=['GET'])
@jwt_required()
def get_track(track_id):
    current_user_id = int(get_jwt_identity())
    track = Track.query.filter_by(id=track_id, user_id=current_user_id).first()
    if not track:
        return jsonify({"message": "Track not found or access denied"}), 404
    return jsonify(track_schema.dump(track)), 200

@bp.route('/<int:track_id>', methods=['PUT'])
@jwt_required()
def update_track(track_id):
    current_user_id = int(get_jwt_identity())
    track = Track.query.filter_by(id=track_id, user_id=current_user_id).first()
    if not track:
        return jsonify({"message": "Track not found or access denied"}), 404

    json_data = request.get_json()
    if not json_data:
        return jsonify({"message": "No input data provided"}), 400

    try:
        # Validate only the fields present in the request
        data = track_update_schema.load(json_data, partial=True) # partial=True allows missing fields
    except ValidationError as err:
        return jsonify(err.messages), 400

    # Update fields if they are provided in the validated data
    for key, value in data.items():
        setattr(track, key, value)

    try:
        db.session.commit()
        return jsonify(track_schema.dump(track)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Could not update track", "error": str(e)}), 500


@bp.route('/<int:track_id>', methods=['DELETE'])
@jwt_required()
def delete_track(track_id):
    current_user_id = int(get_jwt_identity())
    track = Track.query.filter_by(id=track_id, user_id=current_user_id).first()
    if not track:
        return jsonify({"message": "Track not found or access denied"}), 404

    try:
        # Note: Cascading delete should handle removal from playlists if configured correctly
        # Or, you might need to manually remove from playlist_tracks association table first
        # depending on cascade settings and DB constraints. SQLAlchemy cascade should handle this.
        db.session.delete(track)
        db.session.commit()
        return jsonify({"message": "Track deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        # Check for specific integrity errors if needed (e.g., foreign key constraints if cascade fails)
        return jsonify({"message": "Could not delete track", "error": str(e)}), 500
