import re
import os
import uuid
from functools import wraps
from datetime import datetime, timedelta
from flask import request, abort, session, redirect, url_for, flash, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
from models import ActionLog, LoginAttempt, db, UserRole, ServiceOrderImage

def role_required(*roles):
    """Decorator for view functions that require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login', next=request.url))
            
            if current_user.role.name not in roles:
                flash('Você não tem permissão para acessar esta página.', 'danger')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator for view functions that require admin rights"""
    return role_required('admin')(f)

def manager_required(f):
    """Decorator for view functions that require manager or admin rights"""
    return role_required('admin', 'gerente')(f)

def log_action(action, entity_type=None, entity_id=None, details=None):
    """Log user actions in the system"""
    if current_user.is_authenticated:
        log = ActionLog(
            user_id=current_user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

def check_login_attempts(username):
    """Check if the username has exceeded login attempts"""
    from models import User
    
    rate_limit = current_app.config.get('LOGIN_RATE_LIMIT', 5)
    rate_limit_timeout = current_app.config.get('LOGIN_RATE_LIMIT_TIMEOUT', 300)  # 5 minutes
    
    # Buscar email associado ao usuário
    user = User.query.filter_by(username=username).first()
    email = user.email if user else username
    
    # Get recent failed attempts
    cutoff_time = datetime.utcnow() - timedelta(seconds=rate_limit_timeout)
    attempts = LoginAttempt.query.filter(
        LoginAttempt.email == email,
        LoginAttempt.success == False,
        LoginAttempt.timestamp > cutoff_time
    ).count()
    
    return attempts >= rate_limit

def record_login_attempt(username, success):
    """Record login attempt for rate limiting"""
    from models import User
    
    # Buscar email associado ao usuário
    user = User.query.filter_by(username=username).first()
    email = user.email if user else username
    
    attempt = LoginAttempt(
        email=email,
        success=success,
        ip_address=request.remote_addr
    )
    db.session.add(attempt)
    db.session.commit()

def format_document(document):
    """Format CPF/CNPJ for display"""
    # Remove non-digits
    doc = re.sub(r'[^0-9]', '', document)
    
    if len(doc) == 11:  # CPF
        return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
    elif len(doc) == 14:  # CNPJ
        return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
    else:
        return document  # Return as is if invalid

def format_currency(value):
    """Format currency for display"""
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(".", "X").replace(",", ".").replace("X", ",")

def get_monthly_summary():
    """Get financial summary for the current month"""
    from models import FinancialEntry, FinancialEntryType
    from sqlalchemy import func, extract
    
    now = datetime.utcnow()
    
    # Income for current month
    income = db.session.query(func.sum(FinancialEntry.amount)).filter(
        FinancialEntry.type == FinancialEntryType.entrada,
        extract('month', FinancialEntry.date) == now.month,
        extract('year', FinancialEntry.date) == now.year
    ).scalar() or 0
    
    # Expenses for current month
    expenses = db.session.query(func.sum(FinancialEntry.amount)).filter(
        FinancialEntry.type == FinancialEntryType.saida,
        extract('month', FinancialEntry.date) == now.month,
        extract('year', FinancialEntry.date) == now.year
    ).scalar() or 0
    
    return {
        'income': float(income),
        'expenses': float(expenses),
        'balance': float(income - expenses)
    }

def get_service_order_stats():
    """Get service order statistics"""
    from models import ServiceOrder, ServiceOrderStatus
    
    open_count = ServiceOrder.query.filter_by(status=ServiceOrderStatus.aberta).count()
    in_progress_count = ServiceOrder.query.filter_by(status=ServiceOrderStatus.em_andamento).count()
    closed_count = ServiceOrder.query.filter_by(status=ServiceOrderStatus.fechada).count()
    
    return {
        'open': open_count,
        'in_progress': in_progress_count,
        'closed': closed_count,
        'total': open_count + in_progress_count + closed_count
    }

def get_system_setting(name, default=None):
    """Get a system setting by name"""
    from models import SystemSettings
    from app import db
    
    setting = SystemSettings.query.filter_by(name=name).first()
    if setting:
        return setting.value
    
    # If setting doesn't exist and default is provided, create it
    if default is not None:
        setting = SystemSettings(name=name, value=default)
        db.session.add(setting)
        db.session.commit()
        return default
    
    return None

def set_system_setting(name, value, user_id=None):
    """Set a system setting by name"""
    from models import SystemSettings
    from app import db
    
    setting = SystemSettings.query.filter_by(name=name).first()
    if setting:
        setting.value = value
        if user_id:
            setting.updated_by = user_id
    else:
        setting = SystemSettings(name=name, value=value, updated_by=user_id)
        db.session.add(setting)
    
    db.session.commit()
    return True

def get_all_system_settings():
    """Get all system settings as a dictionary"""
    from models import SystemSettings
    
    settings = {}
    for setting in SystemSettings.query.all():
        settings[setting.name] = setting.value
    
    return settings

def get_default_system_settings():
    """Get default system settings"""
    return {
        'theme': 'light',
        'timezone': 'America/Sao_Paulo',
        'date_format': 'DD/MM/YYYY',
        'items_per_page': '20'
    }
    
def save_service_order_images(service_order, images, descriptions=None):
    """
    Salva as imagens enviadas para uma ordem de serviço
    
    Args:
        service_order: Objeto ServiceOrder para o qual as imagens serão salvas
        images: Lista de objetos FileStorage (arquivos enviados)
        descriptions: String com descrições separadas por ponto e vírgula ou None
    
    Returns:
        Lista de objetos ServiceOrderImage criados
    """
    # Criar diretório para imagens se não existir
    upload_folder = os.path.join(current_app.static_folder, 'uploads', 'service_orders', str(service_order.id))
    os.makedirs(upload_folder, exist_ok=True)
    
    # Preparar descrições se fornecidas
    desc_list = []
    if descriptions:
        desc_list = [d.strip() for d in descriptions.split(';') if d.strip()]
    
    saved_images = []
    
    # Processar cada imagem
    for i, image in enumerate(images):
        if image:
            # Gerar nome de arquivo único
            unique_filename = f"{uuid.uuid4()}.jpg"
            
            # Caminho completo para salvar
            filepath = os.path.join(upload_folder, unique_filename)
            
            # Salvar arquivo
            with open(filepath, 'wb') as f:
                f.write(image)
            
            # Criar entrada no banco de dados
            description = desc_list[i] if i < len(desc_list) else None
            image_record = ServiceOrderImage(
                service_order_id=service_order.id,
                filename=f"uploads/service_orders/{service_order.id}/{unique_filename}",
                description=description
            )
            
            db.session.add(image_record)
            saved_images.append(image_record)
    
    if saved_images:
        db.session.commit()
        
    return saved_images
