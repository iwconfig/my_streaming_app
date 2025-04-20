import enum
from app.extensions import db
from datetime import datetime

class ManifestType(enum.Enum):
    HLS = 'HLS'
    DASH = 'DASH'

# Add TrackStatus Enum
class TrackStatus(enum.Enum):
    PENDING = 'PENDING'         # Uploaded, waiting for processing
    PROCESSING = 'PROCESSING'   # FFmpeg/upload in progress
    READY = 'READY'             # Processed, manifest URL available
    ERROR = 'ERROR'             # Processing failed

class Track(db.Model):
    __tablename__ = 'tracks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=True)
    album = db.Column(db.String(200), nullable=True)
    track_number = db.Column(db.Integer, nullable=True)
    duration_ms = db.Column(db.Integer, nullable=True) # FFmpeg can populate this

    manifest_url = db.Column(db.String(1024), nullable=True) # Null until ready
    manifest_type = db.Column(
        db.Enum(ManifestType, native_enum=False),
        nullable=True # Null until ready
    )
    status = db.Column(
        db.Enum(TrackStatus, native_enum=False),
        nullable=False,
        default=TrackStatus.PENDING,
        index=True # Added index
    )
    error_message = db.Column(db.Text, nullable=True) # Store error details

    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationship back to user (already exists, ensure lazy='select' or similar)
    # owner defined via backref in User model

    def __repr__(self):
        return f'<Track {self.id} - {self.title} ({self.status.value})>' # Show status

# Remember to run migrations after changing models:
# flask db migrate -m "Add status/error to Track, nullable manifest, index status"
# flask db upgrade
