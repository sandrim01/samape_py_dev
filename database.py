"""
Database configuration and initialization.
This module handles SQLAlchemy setup to avoid circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Create SQLAlchemy base class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)

def init_db(app):
    """Initialize database with Flask app."""
    db.init_app(app)
    return db
