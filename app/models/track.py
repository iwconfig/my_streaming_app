import enum
from app.extensions import db
from datetime import datetime

class ManifestType(enum.Enum):
    HLS = 'HLS'
    DASH = 'DASH'

class Track(db.Model):
    __tablename__ = 'tracks'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=True)
    album = db.Column(db.String(200), nullable=True)
    track_number = db.Column(db.Integer, nullable=True)
    duration_ms = db.Column(db.Integer, nullable=True) # Optional: store duration if known
    manifest_url = db.Column(db.String(1024), nullable=False) # URL provided by the user
    manifest_type = db.Column(db.Enum(ManifestType), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add other fields like genre, cover_art_url (user provided?) if needed

    def __repr__(self):
        return f'<Track {self.title}>'
