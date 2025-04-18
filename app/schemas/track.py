from app.extensions import ma
from app.models import Track, ManifestType
from marshmallow import fields

class TrackSchema(ma.SQLAlchemyAutoSchema):
    # Convert Enum to string for JSON serialization
    manifest_type = fields.Enum(enum=ManifestType, by_value=True)

    class Meta:
        model = Track
        # load_instance = True
        include_fk = True # Include user_id if needed, or handle via context

# You might want separate schemas for input (loading) vs output (dumping)
class TrackLoadSchema(TrackSchema):
     class Meta(TrackSchema.Meta):
        # Fields required when *adding* a track via API
        exclude = ("id", "added_at", "user_id") # user_id will be set from logged-in user
        # Add required=True to essential fields if not nullable in model
        # title = fields.Str(required=True)
        # manifest_url = fields.Str(required=True)
        # manifest_type = fields.Enum(enum=Track.ManifestType, by_value=True, required=True)

class TrackUpdateSchema(ma.Schema):
     # Define only fields that are allowed to be updated
     title = fields.Str()
     artist = fields.Str()
     album = fields.Str()
     track_number = fields.Int(allow_none=True)
     duration_ms = fields.Int(allow_none=True)
     # Probably don't allow changing manifest_url or type easily? Or maybe yes?
     # manifest_url = fields.Str()
     # manifest_type = fields.Enum(enum=Track.ManifestType, by_value=True)
