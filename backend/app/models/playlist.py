from app.extensions import db
from datetime import datetime

# Association table for the many-to-many relationship between Playlist and Track
playlist_tracks = db.Table('playlist_tracks',
    db.Column('playlist_id', db.Integer, db.ForeignKey('playlists.id'), primary_key=True),
    db.Column('track_id', db.Integer, db.ForeignKey('tracks.id'), primary_key=True),
    db.Column('track_order', db.Integer) # To maintain order within playlist
)

class Playlist(db.Model):
    __tablename__ = 'playlists'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Define the many-to-many relationship
    # Use secondary=playlist_tracks to link via the association table
    # Use order_by to fetch tracks in the specified order
    tracks = db.relationship('Track', secondary=playlist_tracks,
                             # lazy='dynamic', # Use dynamic for querying later
                             backref=db.backref('playlists', lazy=True),
                             order_by="playlist_tracks.c.track_order")

    def __repr__(self):
        return f'<Playlist {self.name}>'
