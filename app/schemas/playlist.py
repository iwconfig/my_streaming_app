from app.extensions import ma
from app.models import Playlist, Track
from .track import TrackSchema
from marshmallow import fields

class PlaylistSchema(ma.SQLAlchemyAutoSchema):
    # Nest tracks within the playlist schema for detailed view
    # Use 'only' to select specific track fields if needed
    tracks = fields.Nested(TrackSchema, many=True, dump_only=True) # dump_only as tracks are added/removed via separate endpoints

    class Meta:
        model = Playlist
        load_instance = True
        include_fk = True # Include user_id

# Schema for creating a playlist (only needs name, maybe description)
class PlaylistCreateSchema(ma.Schema):
    name = fields.Str(required=True)
    description = fields.Str()

# Schema for updating playlist metadata (name, description)
class PlaylistUpdateSchema(ma.Schema):
    name = fields.Str()
    description = fields.Str()

# Schema for adding/removing tracks (needs track ID)
class PlaylistTrackSchema(ma.Schema):
    track_id = fields.Int(required=True)
    order = fields.Int(required=False, allow_none=True) # For setting/updating order

# Schema for reordering all tracks in a playlist
class PlaylistTrackOrderSchema(ma.Schema):
    # Expects a list of track IDs in the desired order
    track_ids = fields.List(fields.Int(), required=True)
