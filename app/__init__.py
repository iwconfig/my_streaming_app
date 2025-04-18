from flask import Flask
from config import Config
from .extensions import db, migrate, ma, jwt, bcrypt, cors
from .routes import register_blueprints
# Import models here to ensure they are known to SQLAlchemy before migrate/create_all
from . import models

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    # Configure CORS more specifically in production if needed
    # cors.init_app(app, resources={r"/api/*": {"origins": "http://yourfrontend.com"}})
    cors.init_app(app) # Allow all origins for now (development)


    # Register Blueprints (API routes)
    register_blueprints(app)

    # Optional: Add a simple root route
    @app.route('/')
    def index():
        return "Music Streamer Backend is running!"

    return app
