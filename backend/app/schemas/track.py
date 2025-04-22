from app.extensions import ma
from app.models import Track, ManifestType, TrackStatus # Import TrackStatus
from marshmallow import fields, validate

# --- Base Schema ---
class TrackSchema(ma.SQLAlchemyAutoSchema):
    # Convert Enums to string for JSON serialization
    manifest_type = fields.Enum(enum=ManifestType, by_value=True, allow_none=True) # Allow none initially
    status = fields.Enum(enum=TrackStatus, by_value=True, dump_only=True) # Status is read-only via API
    error_message = fields.String(dump_only=True) # Usually only show on error

    class Meta:
        model = Track
        load_instance = False # Ensure we get dicts back from load usually
        include_fk = True # Include user_id

# --- Schema for adding by pre-existing URL ---
class TrackLoadURLSchema(ma.Schema):
     title = fields.Str(required=True, validate=validate.Length(min=1))
     artist = fields.Str(allow_none=True)
     album = fields.Str(allow_none=True)
     track_number = fields.Int(allow_none=True)
     duration_ms = fields.Int(allow_none=True)
     manifest_url = fields.URL(required=True) # Use URL validation
     manifest_type = fields.Enum(enum=ManifestType, by_value=True, required=True)

# --- Schema for creating via File Upload (validates form metadata) ---
class TrackUploadMetadataSchema(ma.Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1))
    artist = fields.Str(allow_none=True)
    album = fields.Str(allow_none=True)
    track_number = fields.Int(allow_none=True)
    # --- Add desired output format field ---
    # User specifies HLS or DASH. Validation happens in the route/task.
    output_format = fields.Str(required=False, load_default='HLS', validate=validate.OneOf(['HLS', 'DASH'], error="output_format must be HLS or DASH"))
    # load_default ensures it defaults if not provided

# --- Schema for updating existing track metadata ---
class TrackUpdateSchema(ma.Schema):
     # Only allow updating certain fields
     title = fields.Str(validate=validate.Length(min=1))
     artist = fields.Str(allow_none=True)
     album = fields.Str(allow_none=True)
     track_number = fields.Int(allow_none=True)
     # Don't allow changing processing/status related fields here
