import os
import re
import json
import io
from datetime import datetime
from functools import wraps
from flask import (
    render_template, redirect, url_for, flash, request, jsonify, session, abort,
    current_app, send_file, Response
)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import func, desc, or_
from sqlalchemy.exc import IntegrityError

from wtforms.validators import Optional

from app import db
from models import (
    User, Client, Equipment, ServiceOrder, FinancialEntry, ActionLog,
    UserRole, ServiceOrderStatus, FinancialEntryType, Supplier, Part, PartSale,
    SupplierOrder, OrderItem, OrderStatus, ServiceOrderImage, equipment_service_orders,
    StockItem, StockMovement, StockItemType, StockItemStatus, VehicleType, VehicleStatus,
    Vehicle, VehicleMaintenance, FuelType, MaintenanceType, Refueling, VehicleTravelLog
)
from utils import get_system_setting
from utils import log_action
from forms import (
    LoginForm, UserForm, ClientForm, EquipmentForm, ServiceOrderForm,
    CloseServiceOrderForm, FinancialEntryForm, ProfileForm, SystemSettingsForm,
    SupplierForm, PartForm, PartSaleForm, SupplierOrderForm, OrderItemForm,
    FlaskForm, StockItemForm, StockMovementForm, VehicleForm, VehicleMaintenanceForm
)
from utils import (
    role_required, admin_required, manager_required, log_action,
    check_login_attempts, record_login_attempt, format_document,
    format_currency, get_monthly_summary, get_service_order_stats,
    save_service_order_images, delete_service_order_image,
    identify_and_format_document, recalculate_supplier_order_total,
    get_supplier_order_stats, get_maintenance_in_progress, is_order_paid
)

def register_routes(app):
    # Define o admin_or_manager_required como alias para manager_required
    admin_or_manager_required = manager_required
    
    # Importações necessárias para as rotas
    from datetime import date
    import os
    import uuid
    import base64
    from datetime import timedelta
    from decimal import Decimal
    from io import BytesIO
    from sqlalchemy import and_, or_, not_, extract
    
    # Tratamento para erros 404, 403, 401 e 500
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(401)
    def unauthorized(e):
        return render_template('errors/401.html'), 401
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    
    # Funções de utilidade disponíveis nos templates
    @app.context_processor
    def utility_processor():
        return {
            'now': datetime.now,
            'ServiceOrderStatus': ServiceOrderStatus,
            'FinancialEntryType': FinancialEntryType,
            'OrderStatus': OrderStatus,
            'VehicleStatus': VehicleStatus,
            'MaintenanceType': MaintenanceType,
            'FuelType': FuelType,
            'get_system_setting': get_system_setting,
        }
    
    # Rota inicial - redireciona para login ou dashboard
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))
    
    # Rota de login
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = LoginForm()
        
        if form.validate_on_submit():
            username = form.username.data
            
            # Check if user is rate limited
            if check_login_attempts(username):
                flash('Muitas tentativas de login. Tente novamente mais tarde.', 'danger')
                return render_template('standalone_login.html', form=form)
            
            user = User.query.filter_by(username=username).first()
            
            if user and user.check_password(form.password.data) and user.active:
                try:
                    login_user(user, remember=form.remember_me.data)
                    record_login_attempt(username, True)
                    
                    try:
                        log_action('Login', 'user', user.id)
                    except Exception:
                        # Se falhar o registro de log, continuar sem interferir no fluxo
                        db.session.rollback()
                    
                    next_page = request.args.get('next')
                    if not next_page or not next_page.startswith('/'):
                        next_page = url_for('dashboard')
                    
                    return redirect(next_page)
                except Exception:
                    db.session.rollback()
                    flash('Erro ao efetuar login. Tente novamente.', 'danger')
                    return render_template('standalone_login.html', form=form)
            else:
                try:
                    record_login_attempt(username, False)
                except Exception:
                    db.session.rollback()
                flash('Nome de usuário ou senha inválidos.', 'danger')
        
        return render_template('standalone_login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        # Executar o logout do usuário sem qualquer acesso ao banco de dados
        logout_user()
        flash('Logout efetuado com sucesso.', 'success')
        return redirect(url_for('login'))
    
    # Dashboard
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Obter estatísticas financeiras
        today = datetime.now().date()
        first_day_of_month = date(today.year, today.month, 1)
        
        # Estatísticas do mês
        monthly_stats = get_monthly_summary(first_day_of_month)
        
        # Estatísticas das ordens de serviço
        service_order_stats = get_service_order_stats()
        
        # Obter manutenções em andamento (se houver)
        maintenance_in_progress = get_maintenance_in_progress()
        
        # Obter estatísticas de compras de fornecedores
        supplier_stats = get_supplier_order_stats()
        
        # Renderizar o template com os dados
        return render_template(
            'dashboard.html',
            monthly_stats=monthly_stats,
            service_order_stats=service_order_stats,
            maintenance_in_progress=maintenance_in_progress,
            supplier_stats=supplier_stats
        )
    
    # Ordens de Serviço
    @app.route('/ordens-servico')
    @login_required
    def service_orders():
        # Parâmetros de filtragem
        status_filter = request.args.get('status')
        client_filter = request.args.get('client')
        responsible_filter = request.args.get('responsible')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Consulta base
        query = ServiceOrder.query
        
        # Aplicar filtros
        if status_filter:
            query = query.filter(ServiceOrder.status == status_filter)
        
        if client_filter:
            query = query.filter(ServiceOrder.client_id == client_filter)
        
        if responsible_filter:
            query = query.filter(ServiceOrder.responsible_id == responsible_filter)
        
        if date_from:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(func.date(ServiceOrder.created_at) >= date_from_obj)
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(func.date(ServiceOrder.created_at) <= date_to_obj)
        
        # Ordenar por ID (mais recentes primeiro)
        service_orders = query.order_by(ServiceOrder.id.desc()).all()
        
        # Obter lista de clientes e funcionários para o filtro
        clients = Client.query.order_by(Client.name).all()
        employees = User.query.filter(User.role != 'admin').order_by(User.name).all()
        
        return render_template(
            'service_orders/index.html',
            service_orders=service_orders,
            clients=clients,
            employees=employees,
            status_filter=status_filter,
            client_filter=client_filter,
            responsible_filter=responsible_filter,
            date_from=date_from,
            date_to=date_to,
            ServiceOrderStatus=ServiceOrderStatus
        )
    
    @app.route('/ordens-servico/nova', methods=['GET', 'POST'])
    @login_required
    def new_service_order():
        form = ServiceOrderForm()
        
        # Preencher os selects com dados dinâmicos
        form.client_id.choices = [(0, 'A ser definido')] + [
            (c.id, c.name) for c in Client.query.order_by(Client.name).all()
        ]
        
        if form.validate_on_submit():
            try:
                # Criar nova ordem de serviço
                service_order = ServiceOrder(
                    description=form.description.data,
                    status='aberto',  # Status inicial (aberto)
                    client_id=form.client_id.data if form.client_id.data != 0 else None,
                    responsible_id=current_user.id,
                    created_at=datetime.now(),
                    estimated_value=form.estimated_value.data or 0,
                    discount_amount=0,  # Valor inicial sem desconto
                    original_amount=0,  # Valor original inicialmente zero
                    total_value=form.estimated_value.data or 0  # Valor total inicial igual ao estimado
                )
                
                db.session.add(service_order)
                db.session.commit()
                
                # Adicionar os equipamentos selecionados à OS
                for equipment_id in form.equipment.data:
                    stmt = equipment_service_orders.insert().values(
                        equipment_id=equipment_id,
                        service_order_id=service_order.id
                    )
                    db.session.execute(stmt)
                
                # Registrar as imagens enviadas, se houver
                if form.images.data and any(form.images.data):
                    save_service_order_images(form.images.data, service_order.id)
                
                db.session.commit()
                
                # Registrar os dados da OS no log
                log_action(
                    f"Criação da OS #{service_order.id}",
                    "service_order",
                    service_order.id,
                    f"Nova ordem de serviço criada para o cliente: {service_order.client.name if service_order.client else 'Não definido'}"
                )
                
                flash(f'Ordem de serviço #{service_order.id} criada com sucesso!', 'success')
                return redirect(url_for('view_service_order', id=service_order.id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erro ao criar OS: {str(e)}")
                flash(f'Erro ao criar a ordem de serviço: {str(e)}', 'danger')
        
        # Obter equipamentos para o select múltiplo
        equipments = Equipment.query.order_by(Equipment.brand, Equipment.model).all()
        
        return render_template(
            'service_orders/new.html',
            form=form,
            equipments=equipments
        )

    # Rota para visualizar detalhes de uma ordem de serviço (versão totalmente nova)
    @app.route('/os/<int:id>', methods=['GET'])
    @login_required
    def view_service_order(id):
        try:
            # Consulta direta e simples para obter os dados básicos da OS
            ordem_query = """
                SELECT 
                    id, description, status, created_at, closed_at, 
                    invoice_number, invoice_date, invoice_amount, 
                    service_details, estimated_value, discount_amount, 
                    original_amount, total_value,
                    client_id, responsible_id
                FROM service_order
                WHERE id = :id
            """
            ordem = db.session.execute(
                db.text(ordem_query), 
                {"id": id}
            ).fetchone()
            
            if not ordem:
                flash("Ordem de serviço não encontrada.", "danger")
                return redirect(url_for('service_orders'))
            
            # 1. Obter informações do cliente
            cliente_query = """
                SELECT 
                    name, document, email, phone, address
                FROM client
                WHERE id = :client_id
            """
            cliente_data = db.session.execute(
                db.text(cliente_query), 
                {"client_id": ordem.client_id}
            ).fetchone() if ordem.client_id else None
            
            cliente = {
                'nome': cliente_data.name if cliente_data else None,
                'documento': cliente_data.document if cliente_data else None,
                'email': cliente_data.email if cliente_data else None,
                'telefone': cliente_data.phone if cliente_data else None,
                'endereco': cliente_data.address if cliente_data else None
            }
            
            # 2. Obter informações do responsável
            responsavel_query = """
                SELECT name FROM "user"
                WHERE id = :resp_id
            """
            responsavel_data = db.session.execute(
                db.text(responsavel_query), 
                {"resp_id": ordem.responsible_id}
            ).fetchone() if ordem.responsible_id else None
            
            responsavel = responsavel_data.name if responsavel_data else None
            
            # 3. Obter equipamentos relacionados
            equipamentos_query = """
                SELECT e.id, e.type, e.brand, e.model, e.serial_number 
                FROM equipment e
                JOIN equipment_service_orders eso ON e.id = eso.equipment_id
                WHERE eso.service_order_id = :os_id
            """
            equipamentos = db.session.execute(
                db.text(equipamentos_query), 
                {"os_id": id}
            ).fetchall()
            
            # 4. Obter registros financeiros
            financeiros_query = """
                SELECT id, date, description, type, amount
                FROM financial_entry
                WHERE service_order_id = :os_id
                ORDER BY date DESC
            """
            financeiros = db.session.execute(
                db.text(financeiros_query), 
                {"os_id": id}
            ).fetchall()
            
            # 5. Verificar se o usuário é administrador para exibir controles adicionais
            is_admin = current_user.role == 'admin' if hasattr(current_user, 'role') else False
            
            # Criar objeto para a ordem contendo o responsável e todos os campos
            ordem_completa = {
                'id': ordem.id,
                'description': ordem.description,
                'status': ordem.status,
                'created_at': ordem.created_at,
                'closed_at': ordem.closed_at,
                'invoice_number': ordem.invoice_number,
                'invoice_date': ordem.invoice_date,
                'invoice_amount': ordem.invoice_amount,
                'service_details': ordem.service_details,
                'estimated_value': ordem.estimated_value,
                'discount_amount': ordem.discount_amount,
                'original_amount': ordem.original_amount,
                'total_value': ordem.total_value,
                'responsavel': responsavel
            }
            
            # Renderizar o template com todos os dados necessários
            return render_template(
                'service_orders/simple_view.html',  # Use o novo template
                ordem=ordem_completa,
                cliente=cliente,
                equipamentos=equipamentos,
                financeiros=financeiros,
                is_admin=is_admin
            )
                
        except Exception as e:
            app.logger.error(f"Erro ao visualizar OS #{id}: {str(e)}")
            flash(f"Erro: {str(e)}", "danger")
            return redirect(url_for('service_orders'))
    
    # Rota alternativa redireciona para a implementação principal
    
    @app.route('/ordem/<int:id>/visualizar')
    @login_required
    def view_service_order_alt(id):
        # Simplesmente redireciona para a implementação principal
        return redirect(url_for('view_service_order', id=id))

