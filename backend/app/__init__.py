from flask import Flask
from config import Config
from .extensions import db, migrate, ma, jwt, bcrypt, cors, celery
from .routes import register_blueprints
# Import the media blueprint conditionally later if needed
# from .routes.media import bp as media_bp # <-- Can remove this top-level import
from . import models
import os
import logging # Import logging
from logging.handlers import RotatingFileHandler

log = logging.getLogger(__name__) # Get logger for __init__

# Configure logging to file
# log_file = os.path.join(os.path.dirname(__file__), '../flask.log')
# file_handler = RotatingFileHandler(log_file, maxBytes=10240, backupCount=10)
# file_handler.setLevel(logging.INFO)
# file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
# log.addHandler(file_handler)
log.setLevel(logging.INFO)

log.info('Logging is set up.')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    log.info(f"Creating app with environment: {app.config.get('ENV', 'Not Set (Defaults to production)')}")
    log.info(f"Debug mode: {app.debug}")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    
    # Configure CORS for development
    cors.init_app(app, resources={
        r"/api/*": {
            "origins": ["http://192.168.0.189:5173"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # Initialize Celery (using the existing code)
    celery.conf.update(
        broker_url=app.config['CELERY_BROKER_URL'],
        result_backend=app.config['CELERY_RESULT_BACKEND'],
        imports=app.config['CELERY_IMPORTS']
    )
    class ContextTask(celery.Task):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask
    # Optional explicit task import if needed for discovery
    # from . import tasks # noqa

    # Create directories
    try:
        os.makedirs(app.config['UPLOAD_TEMP_DIR'], exist_ok=True)
        if app.config.get('UPLOAD_PLUGIN', 'local') == 'local':
             os.makedirs(app.config['LOCAL_STORAGE_OUTPUT_DIR'], exist_ok=True)
    except OSError as e:
        app.logger.error(f"Could not create directories: {e}")

    # Register core API Blueprints
    register_blueprints(app)

    # --- Conditionally Register Development Media Server ---
    # Check if Flask is running in development mode (FLASK_ENV=development)
    # Using app.debug is a common shortcut, as it's often True in development
    if app.debug is True:
        try:
            # Import here only if needed
            from .routes.media import bp as media_bp
            app.register_blueprint(media_bp)
            log.warning("!!! Registered DEVELOPMENT media server blueprint at /processed/.")
            log.warning("!!! DO NOT use this in production. Configure Nginx/Caddy instead.")
        except ImportError:
             log.error("Could not import or register development media server blueprint.")
             # Decide if this should be fatal for development
    else:
         log.info("Skipping registration of development media server (app.debug is False).")
         # Ensure directory exists even in production if using local uploader,
         # but don't register the serving route.
         if app.config.get('UPLOAD_PLUGIN', 'local') == 'local':
             try:
                 os.makedirs(app.config['LOCAL_STORAGE_OUTPUT_DIR'], exist_ok=True)
             except OSError as e:
                 app.logger.error(f"Could not create LOCAL_STORAGE_OUTPUT_DIR in non-debug mode: {e}")


    @app.route('/')
    def index():
        return "Music Streamer Backend is running!"

    return app
