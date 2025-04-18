import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

class Config:
    # Default to a local SQLite file if DATABASE_URL is not set in .env
    DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'app_data.db')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', f'sqlite:///{DEFAULT_SQLITE_PATH}')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key') # CHANGE THIS IN PRODUCTION
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'another_secret_key') # CHANGE THIS IN PRODUCTION
    # JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
