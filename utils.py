import re
import os
import uuid
from functools import wraps
from datetime import datetime, timedelta
from flask import request, abort, session, redirect, url_for, flash, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename
from models import ActionLog, LoginAttempt, db, UserRole, ServiceOrderImage, FinancialEntry

def identify_and_format_document(document):
    """Identifica se é CPF ou CNPJ e formata adequadamente"""
    if not document:
        return document
        
    # Remove todos os caracteres não numéricos
    digits = ''.join(filter(str.isdigit, str(document)))
    
    # Formata como CPF (xxx.xxx.xxx-xx)
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    # Formata como CNPJ (xx.xxx.xxx/xxxx-xx)
    elif len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    
    # Retorna como está se não for reconhecido
    return document

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
    from sqlalchemy.exc import IntegrityError
    
    if current_user.is_authenticated:
        try:
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
        except IntegrityError:
            # Se houver erro de integridade, fazer rollback e não registrar
            db.session.rollback()
            # Não impedir o fluxo normal da aplicação

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
    from sqlalchemy.exc import IntegrityError
    
    try:
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
    except IntegrityError:
        # Em caso de erro de integridade, fazer rollback e não registrar
        db.session.rollback()
        # Não impede o login/logout, apenas desativa o registro desta tentativa

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
    from sqlalchemy import func
    
    open_count = ServiceOrder.query.filter_by(status=ServiceOrderStatus.aberta).count()
    in_progress_count = ServiceOrder.query.filter_by(status=ServiceOrderStatus.em_andamento).count()
    closed_count = ServiceOrder.query.filter_by(status=ServiceOrderStatus.fechada).count()
    
    # Calcular o tempo médio de conclusão (em dias)
    avg_completion_time = 0
    closed_orders_with_dates = ServiceOrder.query.filter(
        ServiceOrder.status == ServiceOrderStatus.fechada,
        ServiceOrder.created_at.isnot(None),
        ServiceOrder.closed_at.isnot(None)
    ).all()
    
    if closed_orders_with_dates:
        total_days = 0
        for order in closed_orders_with_dates:
            # Calcular a diferença em dias
            delta = order.closed_at - order.created_at
            total_days += delta.days
        
        if len(closed_orders_with_dates) > 0:
            avg_completion_time = round(total_days / len(closed_orders_with_dates), 1)
    
    return {
        'open': open_count,
        'in_progress': in_progress_count,
        'closed': closed_count,
        'total': open_count + in_progress_count + closed_count,
        'avg_completion_time': avg_completion_time
    }
    
def get_supplier_order_stats():
    """Get supplier order statistics"""
    from models import SupplierOrder, OrderStatus
    
    pending_count = SupplierOrder.query.filter_by(status=OrderStatus.pendente).count()
    approved_count = SupplierOrder.query.filter_by(status=OrderStatus.aprovado).count()
    sent_count = SupplierOrder.query.filter_by(status=OrderStatus.enviado).count()
    received_count = SupplierOrder.query.filter_by(status=OrderStatus.recebido).count()
    canceled_count = SupplierOrder.query.filter_by(status=OrderStatus.cancelado).count()
    
    open_orders = pending_count + approved_count + sent_count
    closed_orders = received_count + canceled_count
    
    return {
        'pending': pending_count,
        'approved': approved_count,
        'sent': sent_count,
        'received': received_count,
        'canceled': canceled_count,
        'open': open_orders,
        'closed': closed_orders,
        'total': open_orders + closed_orders
    }
    
def get_maintenance_in_progress():
    """Get a list of maintenance orders in progress"""
    from models import ServiceOrder, ServiceOrderStatus
    
    in_progress_orders = ServiceOrder.query.filter_by(
        status=ServiceOrderStatus.em_andamento
    ).order_by(
        ServiceOrder.created_at.desc()
    ).limit(5).all()
    
    return in_progress_orders

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
        if image and hasattr(image, 'filename') and image.filename:
            # Gerar nome de arquivo único
            extension = os.path.splitext(image.filename)[1] or '.jpg'
            unique_filename = f"{uuid.uuid4()}{extension}"
            
            # Caminho completo para salvar
            filepath = os.path.join(upload_folder, unique_filename)
            
            # Salvar arquivo
            image.save(filepath)
            
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

def delete_service_order_image(image_id):
    """
    Remove uma imagem de ordem de serviço do sistema de arquivos e do banco de dados
    
    Args:
        image_id: ID da imagem a ser removida
        
    Returns:
        Tupla (sucesso, mensagem)
    """
    from models import ServiceOrderImage
    from flask import current_app
    
    # Buscar imagem no banco de dados
    image = ServiceOrderImage.query.get(image_id)
    if not image:
        return False, "Imagem não encontrada"
    
    try:
        # Obter o caminho físico do arquivo
        file_path = os.path.join(current_app.static_folder, image.filename)
        
        # Remover arquivo do sistema de arquivos se existir
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remover registro do banco de dados
        db.session.delete(image)
        db.session.commit()
        
        return True, "Imagem removida com sucesso"
    except Exception as e:
        db.session.rollback()
        return False, f"Erro ao remover imagem: {str(e)}"
        
def get_next_invoice_number():
    """
    Gera um número sequencial para nota fiscal
    
    Returns:
        String formatada com o próximo número de nota fiscal
    """
    from models import SequenceCounter
    from flask import current_app
    
    # Busca o contador de NF-e ou cria se não existir
    counter = SequenceCounter.query.filter_by(name='nfe').first()
    if not counter:
        # Inicializa o contador de NF-e
        counter = SequenceCounter(
            name='nfe',
            prefix='NF',
            current_value=0,  # Começará do 1 ao chamar next_value()
            padding=8,
            description='Contador de notas fiscais eletrônicas'
        )
        db.session.add(counter)
        db.session.commit()
    
    # Retorna o próximo valor da sequência
    return counter.next_value()
    
def recalculate_supplier_order_total(order_id):
    """
    Recalcula o valor total do pedido de fornecedor com base nos itens
    
    Args:
        order_id: ID do pedido de fornecedor
        
    Returns:
        Decimal: O novo valor total calculado
    """
    from models import SupplierOrder, OrderItem
    from sqlalchemy import func
    
    # Calcula a soma dos valores totais dos itens
    total = db.session.query(func.sum(OrderItem.total_price)).filter(
        OrderItem.order_id == order_id
    ).scalar() or 0
    
    # Atualiza o valor total no pedido
    order = SupplierOrder.query.get(order_id)
    if order:
        order.total_value = total
        db.session.commit()
        
    return total
    
def is_order_paid(order_id):
    """
    Verifica se um pedido já tem pagamento registrado no financeiro
    
    Args:
        order_id: ID do pedido de fornecedor
        
    Returns:
        Boolean: True se o pedido já foi pago, False caso contrário
    """
    financial_entry = FinancialEntry.query.filter_by(
        entry_type='pedido_fornecedor',
        reference_id=order_id
    ).first()
    
    return financial_entry is not None
