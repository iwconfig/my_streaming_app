from flask import Blueprint

# Import blueprints from individual route files
from .auth import bp as auth_bp
from .tracks import bp as tracks_bp
from .playlists import bp as playlists_bp

def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(tracks_bp, url_prefix='/api/tracks')
    app.register_blueprint(playlists_bp, url_prefix='/api/playlists')
