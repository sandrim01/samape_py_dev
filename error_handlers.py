"""
Exception handling utilities for SAMAPE application.
"""
import logging
from functools import wraps
from flask import flash, redirect, url_for, current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from werkzeug.exceptions import BadRequest, NotFound, Forbidden, InternalServerError
from database import db

logger = logging.getLogger(__name__)

def handle_database_error(func):
    """Decorator to handle database errors consistently."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Database integrity error in {func.__name__}: {e}")
            flash('Erro de integridade dos dados. Verifique se os dados não estão duplicados.', 'danger')
            return redirect(url_for('dashboard'))
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error in {func.__name__}: {e}")
            flash('Erro no banco de dados. Tente novamente.', 'danger')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            flash('Erro inesperado. Contacte o suporte técnico.', 'danger')
            return redirect(url_for('dashboard'))
    return wrapper

def log_and_flash_error(error_msg, exception=None, flash_msg=None, level='error'):
    """Log an error and optionally flash a message to the user."""
    if exception:
        getattr(logger, level)(f"{error_msg}: {exception}")
    else:
        getattr(logger, level)(error_msg)
    
    if flash_msg:
        flash(flash_msg, 'danger')

def safe_db_operation(operation, success_msg=None, error_msg=None):
    """Safely execute a database operation with proper error handling."""
    try:
        result = operation()
        db.session.commit()
        if success_msg:
            flash(success_msg, 'success')
        return result
    except IntegrityError as e:
        db.session.rollback()
        log_and_flash_error(
            f"Integrity error during database operation", 
            e, 
            error_msg or "Erro de integridade dos dados."
        )
        return None
    except SQLAlchemyError as e:
        db.session.rollback()
        log_and_flash_error(
            f"Database error during operation", 
            e, 
            error_msg or "Erro no banco de dados."
        )
        return None
    except Exception as e:
        db.session.rollback()
        log_and_flash_error(
            f"Unexpected error during database operation", 
            e, 
            error_msg or "Erro inesperado."
        )
        return None

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

class BusinessLogicError(Exception):
    """Custom exception for business logic violations."""
    pass
