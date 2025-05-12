import os
from datetime import timedelta

class Config:
    # Flask
    SECRET_KEY = os.environ.get("SESSION_SECRET", "development_key")
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "postgresql://postgres:qUngJAyBvLWQdkmSkZEjjEoMoDVzOBnx@trolley.proxy.rlwy.net:22285/railway")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # Rate limiting
    LOGIN_RATE_LIMIT = 5  # Number of attempts
    LOGIN_RATE_LIMIT_TIMEOUT = 300  # Seconds (5 minutes)
    
    # Application
    APP_NAME = "SAMAPE - Sistema de Gestão de Serviços"
    COMPANY_NAME = "SAMAPE"
    
    # Roles
    ROLES = ["admin", "gerente", "funcionario"]
