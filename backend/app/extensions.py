from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from celery import Celery # Import Celery

db = SQLAlchemy()
migrate = Migrate()
ma = Marshmallow()
jwt = JWTManager()
bcrypt = Bcrypt()
cors = CORS()

# Initialize Celery here, configuration happens in create_app
# Use backend name for easier identification if multiple apps use same broker
# Use the first part of the package name (e.g., 'app')
celery = Celery(__name__.split('.')[0]) # Name defaults to 'app'
