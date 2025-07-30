import os
from datetime import timedelta

class Config:
    """Base configuration class."""
    # Flask
    SECRET_KEY = os.environ.get("SESSION_SECRET")
    if not SECRET_KEY:
        raise ValueError("SESSION_SECRET environment variable is required")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL environment variable is required")
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    WTF_CSRF_SSL_STRICT = os.environ.get('FLASK_ENV') == 'production'
    
    # Rate limiting
    LOGIN_RATE_LIMIT = int(os.environ.get('LOGIN_RATE_LIMIT', '5'))
    LOGIN_RATE_LIMIT_TIMEOUT = int(os.environ.get('LOGIN_RATE_LIMIT_TIMEOUT', '300'))
    
    # Upload settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/uploads')
    
    # Application
    APP_NAME = "SAMAPE - Sistema de Gestão de Serviços"
    COMPANY_NAME = "SAMAPE"
    APP_VERSION = "2.0"
    
    # Roles
    ROLES = ["admin", "gerente", "funcionario"]

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    WTF_CSRF_SSL_STRICT = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    WTF_CSRF_SSL_STRICT = True
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
