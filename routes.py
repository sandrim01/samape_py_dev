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
    from werkzeug.utils import secure_filename
    
    # Error handlers
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

    # Context processors
    @app.context_processor
    def utility_processor():
        from utils import get_system_setting
        return {
            'format_document': format_document,
            'format_currency': format_currency,
            'UserRole': UserRole,
            'ServiceOrderStatus': ServiceOrderStatus,
            'FinancialEntryType': FinancialEntryType,
            'now': datetime.utcnow,
            'get_system_setting': get_system_setting
        }

    # Authentication routes
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))

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
                return render_template('login.html', form=form)
            
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
                    return render_template('login.html', form=form)
            else:
                try:
                    record_login_attempt(username, False)
                except Exception:
                    db.session.rollback()
                flash('Nome de usuário ou senha inválidos.', 'danger')
        
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        # Executar o logout do usuário sem qualquer acesso ao banco de dados
        logout_user()
        
        # Feedback para o usuário
        flash('Você foi desconectado com sucesso.', 'success')
        
        # Redirecionar para a página de login
        return redirect(url_for('login'))

    # Dashboard
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Get service order statistics
        so_stats = get_service_order_stats()
        
        # Get supplier order statistics
        supplier_stats = get_supplier_order_stats()
        
        # Get financial summary
        financial_summary = get_monthly_summary()
        
        # Get maintenance in progress
        maintenance_in_progress = get_maintenance_in_progress()
        
        # Get recent service orders
        recent_orders = ServiceOrder.query.order_by(
            ServiceOrder.created_at.desc()
        ).limit(5).all()
        
        # Get recent activity logs
        recent_logs = ActionLog.query.order_by(
            ActionLog.timestamp.desc()
        ).limit(10).all()
        
        # Get pending supplier orders
        pending_supplier_orders = SupplierOrder.query.filter(
            SupplierOrder.status.in_([OrderStatus.pendente, OrderStatus.aprovado, OrderStatus.enviado])
        ).order_by(SupplierOrder.created_at.desc()).limit(5).all()
        
        # Get low stock items (EPIs e ferramentas)
        low_stock_items = StockItem.query.filter(
            StockItem.quantity <= StockItem.min_quantity
        ).order_by(StockItem.quantity.asc()).limit(5).all()
        
        # Get parts with low stock (peças)
        low_stock_parts = Part.query.filter(
            Part.stock_quantity <= Part.minimum_stock
        ).order_by(Part.stock_quantity.asc()).limit(5).all()
        
        # Add current timestamp to prevent caching
        from datetime import datetime
        
        # Prepare metrics for dashboard
        import json
        metrics = {
            'pending_orders': so_stats['open'],
            'in_progress_orders': so_stats['in_progress'],
            'closed_orders': so_stats['closed'],
            'avg_completion_time': so_stats['avg_completion_time'],
            'efficiency_percentage': min(100, so_stats['avg_completion_time'] * 10) if so_stats['avg_completion_time'] > 0 else 50,
            'open_orders': supplier_stats['open'],
            'pending_delivery': supplier_stats['sent'],
            'delivered_this_month': supplier_stats['received'],
            'monthly_income': financial_summary['income'],
            'monthly_expenses': financial_summary['expenses'],
            'income_data': json.dumps([financial_summary['income']/6, financial_summary['income']/3, financial_summary['income']/2, financial_summary['income']/1.5, financial_summary['income']/1.2, financial_summary['income']]),
            'expense_data': json.dumps([financial_summary['expenses']/6, financial_summary['expenses']/4, financial_summary['expenses']/3, financial_summary['expenses']/2, financial_summary['expenses']/1.3, financial_summary['expenses']])
        }
        
        # Adicionar estatísticas da frota
        metrics.update({
            'fleet_active': Vehicle.query.filter_by(status=VehicleStatus.ativo).count(),
            'fleet_maintenance': Vehicle.query.filter_by(status=VehicleStatus.em_manutencao).count(),
            'fleet_inactive': Vehicle.query.filter_by(status=VehicleStatus.inativo).count(),
            'fleet_reserved': 0,  # Valor padrão para manter compatibilidade com o template
            'fleet_total': Vehicle.query.count()
        })
        
        return render_template(
            'dashboard.html',
            so_stats=so_stats,
            supplier_stats=supplier_stats,
            financial_summary=financial_summary,
            maintenance_in_progress=maintenance_in_progress,
            recent_orders=recent_orders,
            recent_logs=recent_logs,
            pending_supplier_orders=pending_supplier_orders,
            low_stock_items=low_stock_items,
            low_stock_parts=low_stock_parts,
            metrics=metrics,
            now=datetime.now().timestamp()
        )

    # Service Order routes
    @app.route('/os')
    @login_required
    def service_orders():
        status_filter = request.args.get('status', '')
        client_filter = request.args.get('client', '')
        responsible_filter = request.args.get('responsible', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        query = ServiceOrder.query
        
        # Apply filters
        if status_filter:
            query = query.filter(ServiceOrder.status == status_filter)
        
        if client_filter:
            query = query.filter(ServiceOrder.client_id == client_filter)
        
        if responsible_filter:
            query = query.filter(ServiceOrder.responsible_id == responsible_filter)
        
        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(ServiceOrder.created_at >= date_from)
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d')
                query = query.filter(ServiceOrder.created_at <= date_to)
            except ValueError:
                pass
        
        service_orders = query.order_by(ServiceOrder.created_at.desc()).all()
        clients = Client.query.order_by(Client.name).all()
        employees = User.query.filter_by(active=True).order_by(User.name).all()
        
        return render_template(
            'service_orders/index.html',
            service_orders=service_orders,
            clients=clients,
            employees=employees,
            status_filter=status_filter,
            client_filter=client_filter,
            responsible_filter=responsible_filter,
            date_from=date_from,
            date_to=date_to
        )

    @app.route('/os/nova', methods=['GET', 'POST'])
    @login_required
    def new_service_order():
        form = ServiceOrderForm()
        
        # Load clients for dropdown
        form.client_id.choices = [(c.id, c.name) for c in Client.query.order_by(Client.name).all()]
        
        # Load employees for dropdown
        form.responsible_id.choices = [(0, 'A ser definido')] + [
            (u.id, u.name) for u in User.query.filter_by(active=True).order_by(User.name).all()
        ]
        
        if form.validate_on_submit():
            try:
                service_order = ServiceOrder(
                    client_id=form.client_id.data,
                    responsible_id=form.responsible_id.data if form.responsible_id.data != 0 else None,
                    description=form.description.data,
                    estimated_value=form.estimated_value.data,
                    status=ServiceOrderStatus[form.status.data]
                )
                
                # Add equipment relationships if selected
                if form.equipment_ids.data:
                    equipment_ids = form.equipment_ids.data.split(',')
                    for eq_id in equipment_ids:
                        equipment = Equipment.query.get(int(eq_id))
                        if equipment and equipment.client_id == service_order.client_id:
                            service_order.equipment.append(equipment)
                
                db.session.add(service_order)
                db.session.commit()
                
                # Processar imagens - verificar se há arquivos enviados
                try:
                    image_files = request.files.getlist('images')
                    if image_files and any(f.filename for f in image_files):
                        saved_images = save_service_order_images(
                            service_order, 
                            image_files, 
                            form.image_descriptions.data
                        )
                        if saved_images:
                            flash(f'{len(saved_images)} imagem(ns) anexada(s) com sucesso!', 'info')
                except Exception as img_error:
                    # Se falhar ao salvar as imagens, registre o erro mas não interrompa o fluxo
                    flash(f'Aviso: Não foi possível salvar as imagens: {str(img_error)}', 'warning')
                
                try:
                    log_action(
                        'Criação de OS',
                        'service_order',
                        service_order.id,
                        f"OS criada para cliente {service_order.client.name}"
                    )
                except Exception:
                    # Se falhar ao registrar o log, não interromper o fluxo principal
                    pass
                
                flash('Ordem de serviço criada com sucesso!', 'success')
                return redirect(url_for('service_orders'))
            
            except IntegrityError:
                db.session.rollback()
                flash('Erro de integridade ao criar a ordem de serviço. O ID pode estar duplicado.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao criar ordem de serviço: {str(e)}', 'danger')
            
        return render_template(
            'service_orders/create.html',
            form=form
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
    
    # Rota para excluir uma ordem de serviço (nova implementação)
    @app.route('/os/<int:id>/excluir', methods=['GET', 'POST'])
    @login_required
    def delete_service_order_new(id):
        # Verificar se o usuário é administrador
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            flash("Apenas administradores podem excluir ordens de serviço.", "danger")
            return redirect(url_for('service_orders'))
            
        try:
            # Primeiro, verificar se a OS existe
            ordem = db.session.execute(db.text("""
                SELECT id FROM service_order WHERE id = :id
            """), {"id": id}).fetchone()
            
            if not ordem:
                flash("Ordem de serviço não encontrada.", "danger")
                return redirect(url_for('service_orders'))
                
            # Para GET, mostrar página de confirmação
            if request.method == 'GET':
                return render_template('service_orders/delete_confirm.html', id=id)
                
            # Para POST, realizar a exclusão
            
            # 1. Excluir associações com equipamentos
            db.session.execute(db.text("""
                DELETE FROM equipment_service_orders
                WHERE service_order_id = :id
            """), {"id": id})
            
            # 2. Excluir registros financeiros
            db.session.execute(db.text("""
                DELETE FROM financial_entry
                WHERE service_order_id = :id
            """), {"id": id})
            
            # 3. Excluir a ordem de serviço
            db.session.execute(db.text("""
                DELETE FROM service_order
                WHERE id = :id
            """), {"id": id})
            
            # Confirmar transação
            db.session.commit()
            
            # Registrar no log
            try:
                log_action(f"Exclusão da OS #{id}", "service_order", id, f"OS #{id} excluída por {current_user.name}")
            except Exception as log_error:
                app.logger.warning(f"Erro ao registrar log de exclusão: {str(log_error)}")
                
            flash(f"Ordem de serviço #{id} excluída com sucesso.", "success")
            return redirect(url_for('service_orders'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erro ao excluir OS #{id}: {str(e)}")
            flash(f"Erro ao excluir ordem de serviço: {str(e)}", "danger")
            return redirect(url_for('service_orders'))
    
    # Rota para visualizar OS com tratamento especial (nova versão completa)
    @app.route('/ordem/<int:id>/visualizar')
    @login_required
    def view_service_order_alt(id):
        # Redirecionar para a implementação principal
        return redirect(url_for('view_service_order', id=id))

# Registro de pagamento de pedido a fornecedor
    @app.route('/pedidos-fornecedor/<int:id>/registrar-pagamento', methods=['POST'])
    @login_required
    def register_supplier_order_payment(id):
        order = SupplierOrder.query.get_or_404(id)
        
        # Verificar se o pedido já foi pago
        financial_entry = FinancialEntry.query.filter_by(
            description=f'Pagamento de Pedido #{order.id} - {order.supplier.name}',
            entry_type='pedido_fornecedor',
            reference_id=order.id
        ).first()
        
        if financial_entry:
            flash('Este pedido já foi registrado como pago!', 'warning')
            return redirect(url_for('view_supplier_order', id=order.id))
        
        # Criar entrada financeira como despesa
        financial_entry = FinancialEntry(
            description=f'Pagamento de Pedido #{order.id} - {order.supplier.name}',
            amount=order.total_value,
            type=FinancialEntryType.saida,
            date=datetime.utcnow(),
            created_by=current_user.id,
            entry_type='pedido_fornecedor',
            reference_id=order.id
        )
        
        # Atualizar status do pedido para 'recebido'
        order.status = OrderStatus.recebido
        
        db.session.add(financial_entry)
        db.session.commit()
        
        # Registrar ação no log
        log_action(
            'Pagamento de Pedido',
            'supplier_order',
            order.id,
            f'Pagamento de pedido para {order.supplier.name} no valor de {format_currency(order.total_value)}'
        )
        
        flash(f'Pagamento de {format_currency(order.total_value)} registrado com sucesso!', 'success')
        return redirect(url_for('view_supplier_order', id=order.id))
    
    # System Settings
    @app.route('/configuracoes', methods=['GET', 'POST'])
    @login_required
    def system_settings():
        from utils import get_all_system_settings, get_default_system_settings, set_system_setting
        
        # Get current settings or use defaults
        default_settings = get_default_system_settings()
        current_settings = get_all_system_settings()
        
        # Merge defaults with current settings
        for key, value in default_settings.items():
            if key not in current_settings:
                current_settings[key] = value
        
        form = SystemSettingsForm()
        
        # Pre-populate form with current settings
        if request.method == 'GET':
            form.theme.data = current_settings.get('theme', 'light')
            form.timezone.data = current_settings.get('timezone', 'America/Sao_Paulo')
            form.date_format.data = current_settings.get('date_format', 'DD/MM/YYYY')
            form.items_per_page.data = int(current_settings.get('items_per_page', '20'))
        
        if form.validate_on_submit():
            # Save settings
            set_system_setting('theme', form.theme.data, current_user.id)
            set_system_setting('timezone', form.timezone.data, current_user.id)
            set_system_setting('date_format', form.date_format.data, current_user.id)
            set_system_setting('items_per_page', str(form.items_per_page.data), current_user.id)
            
            log_action('Atualização de Configurações', 'system', None, 'Configurações do sistema atualizadas')
            
            flash('Configurações atualizadas com sucesso!', 'success')
            return redirect(url_for('system_settings'))
            
        return render_template('settings/index.html', form=form, settings=current_settings)
        
    # Rotas para gerenciamento de EPIs e ferramentas (estoque)
    @app.route('/estoque', methods=['GET'])
    @login_required
    def stock_items():
        # Parâmetros de filtro
        item_type = request.args.get('type', '')
        status = request.args.get('status', '')
        search = request.args.get('search', '')
        supplier_id = request.args.get('supplier_id', '')
        
        # Query base com ordenação padrão
        query = StockItem.query
        
        # Aplicar filtros
        if item_type:
            query = query.filter(StockItem.type == StockItemType[item_type])
        if status:
            query = query.filter(StockItem.status == StockItemStatus[status])
        if search:
            query = query.filter(StockItem.name.ilike(f'%{search}%') | 
                                StockItem.description.ilike(f'%{search}%'))
        if supplier_id and supplier_id.isdigit():
            query = query.filter(StockItem.supplier_id == int(supplier_id))
        
        # Atualizar status de todos os itens
        items_to_update = []
        for item in query.all():
            old_status = item.status
            item.update_status()
            if old_status != item.status:
                items_to_update.append(item)
        
        if items_to_update:
            db.session.commit()
        
        # Ordenação e paginação
        items_per_page = int(get_system_setting('items_per_page', '20'))
        page = request.args.get('page', 1, type=int)
        items = query.order_by(StockItem.name).paginate(
            page=page, per_page=items_per_page, error_out=False
        )
        
        # Lista de fornecedores para o filtro
        suppliers = Supplier.query.order_by(Supplier.name).all()
        
        # Lista completa de itens para o modal de movimentação
        all_stock_items = StockItem.query.order_by(StockItem.name).all()
        
        return render_template(
            'stock/index.html',
            items=items,
            all_stock_items=all_stock_items,
            item_types=StockItemType,
            item_statuses=StockItemStatus,
            suppliers=suppliers,
            active_filters={
                'type': item_type,
                'status': status,
                'search': search,
                'supplier_id': supplier_id
            },
            type_filter=item_type
        )
        
    @app.route('/estoque/novo', methods=['GET', 'POST'])
    @login_required
    def new_stock_item():
        form = StockItemForm()
        
        if form.validate_on_submit():
            try:
                # Processar data de validade
                expiration_date = None
                if form.expiration_date.data:
                    try:
                        expiration_date = datetime.strptime(form.expiration_date.data, '%Y-%m-%d').date()
                    except ValueError:
                        flash('Formato de data inválido. Use o formato AAAA-MM-DD.', 'danger')
                        return render_template('stock/edit.html', form=form)
                
                # Criar o item
                stock_item = StockItem(
                    name=form.name.data,
                    description=form.description.data,
                    type=StockItemType[form.type.data],
                    quantity=form.quantity.data,
                    min_quantity=form.min_quantity.data,
                    location=form.location.data,
                    price=form.price.data,
                    supplier_id=form.supplier_id.data if form.supplier_id.data != 0 else None,
                    expiration_date=expiration_date,
                    ca_number=form.ca_number.data,
                    created_by=current_user.id
                )
                
                # Atualizar status com base na quantidade e validade
                stock_item.update_status()
                
                # Salvar imagem se fornecida
                if form.image.data and form.image.data.filename:
                    filename = secure_filename(form.image.data.filename)
                    # Gerar nome único com uuid
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    # Diretório para salvar as imagens
                    upload_folder = os.path.join(current_app.static_folder, 'uploads', 'stock')
                    os.makedirs(upload_folder, exist_ok=True)
                    # Caminho completo do arquivo
                    filepath = os.path.join(upload_folder, unique_filename)
                    # Salvar o arquivo
                    form.image.data.save(filepath)
                    # Armazenar o caminho relativo no banco de dados
                    stock_item.image = f'uploads/stock/{unique_filename}'
                
                db.session.add(stock_item)
                db.session.commit()
                
                # Registrar a criação do item
                log_action(
                    'Cadastro de Item de Estoque',
                    'stock_item',
                    stock_item.id,
                    f"Item {stock_item.name} cadastrado no estoque"
                )
                
                # Criar um registro de movimento de estoque para a entrada inicial
                if form.quantity.data > 0:
                    movement = StockMovement(
                        stock_item_id=stock_item.id,
                        quantity=form.quantity.data,
                        description="Entrada inicial de estoque",
                        created_by=current_user.id
                    )
                    db.session.add(movement)
                    db.session.commit()
                
                flash('Item cadastrado com sucesso!', 'success')
                return redirect(url_for('view_stock_item', id=stock_item.id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erro ao cadastrar item de estoque: {str(e)}")
                flash(f'Erro ao cadastrar item: {str(e)}', 'danger')
        
        return render_template('stock/edit.html', form=form, item=None)
        
    @app.route('/estoque/<int:id>', methods=['GET'])
    @login_required
    def view_stock_item(id):
        item = StockItem.query.get_or_404(id)
        
        # Atualizar status do item
        old_status = item.status
        item.update_status()
        if old_status != item.status:
            db.session.commit()
        
        # Buscar movimentações do item
        movements = StockMovement.query.filter_by(stock_item_id=id).order_by(StockMovement.created_at.desc()).all()
        
        # Formulário para nova movimentação
        movement_form = StockMovementForm()
        movement_form.stock_item_id.choices = [(item.id, item.name)]
        movement_form.stock_item_id.data = item.id
        
        return render_template(
            'stock/view.html',
            item=item,
            movements=movements,
            movement_form=movement_form,
            now=datetime.now()
        )
        
    @app.route('/estoque/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    def edit_stock_item(id):
        item = StockItem.query.get_or_404(id)
        form = StockItemForm(obj=item)
        
        if form.validate_on_submit():
            try:
                # Processar data de validade
                expiration_date = None
                if form.expiration_date.data:
                    try:
                        expiration_date = datetime.strptime(form.expiration_date.data, '%Y-%m-%d').date()
                    except ValueError:
                        flash('Formato de data inválido. Use o formato AAAA-MM-DD.', 'danger')
                        return render_template('stock/edit.html', form=form, item=item)
                
                # Atualizar o item
                item.name = form.name.data
                item.description = form.description.data
                item.type = StockItemType[form.type.data]
                # Não atualizar quantity diretamente, usar movimentação
                item.min_quantity = form.min_quantity.data
                item.location = form.location.data
                item.price = form.price.data
                item.supplier_id = form.supplier_id.data if form.supplier_id.data != 0 else None
                item.expiration_date = expiration_date
                item.ca_number = form.ca_number.data
                
                # Salvar nova imagem se fornecida
                if form.image.data and form.image.data.filename:
                    # Remover imagem anterior se existir
                    if item.image:
                        old_image_path = os.path.join(current_app.static_folder, item.image)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    
                    filename = secure_filename(form.image.data.filename)
                    # Gerar nome único com uuid
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    # Diretório para salvar as imagens
                    upload_folder = os.path.join(current_app.static_folder, 'uploads', 'stock')
                    os.makedirs(upload_folder, exist_ok=True)
                    # Caminho completo do arquivo
                    filepath = os.path.join(upload_folder, unique_filename)
                    # Salvar o arquivo
                    form.image.data.save(filepath)
                    # Armazenar o caminho relativo no banco de dados
                    item.image = f'uploads/stock/{unique_filename}'
                
                # Atualizar status do item
                item.update_status()
                db.session.commit()
                
                # Registrar a edição do item
                log_action(
                    'Edição de Item de Estoque',
                    'stock_item',
                    item.id,
                    f"Item {item.name} editado no estoque"
                )
                
                flash('Item atualizado com sucesso!', 'success')
                return redirect(url_for('view_stock_item', id=item.id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erro ao editar item de estoque: {str(e)}")
                flash(f'Erro ao editar item: {str(e)}', 'danger')
        
        # Preencher o campo de data de validade no formato correto
        if request.method == 'GET' and item.expiration_date:
            form.expiration_date.data = item.expiration_date.strftime('%Y-%m-%d')
        
        return render_template('stock/edit.html', form=form, item=item)
        
    @app.route('/estoque/<int:id>/excluir', methods=['POST'])
    @login_required
    # Permitir que funcionários também excluam itens de estoque
    def delete_stock_item(id):
        # Solução simplificada para resolver problemas de transação
        from flask import current_app
        
        # Garantir que qualquer operação pendente seja encerrada
        db.session.close()
        
        try:
            # Remover diretamente da base de dados usando SQL bruto para evitar problemas com SQLAlchemy
            # Executando cada operação em uma transação independente
            
            # 1. Obter informações do item antes de excluir
            item = StockItem.query.get_or_404(id)
            item_name = item.name
            item_image = item.image
            
            # 2. Excluir movimentações primeiro
            from sqlalchemy import text
            db.session.execute(text("DELETE FROM stock_movement WHERE stock_item_id = :id"), {"id": id})
            db.session.commit()
            
            # 3. Excluir o item
            db.session.execute(text("DELETE FROM stock_item WHERE id = :id"), {"id": id})
            db.session.commit()
            
            # 4. Remover imagem se existir
            if item_image:
                try:
                    image_path = os.path.join(current_app.root_path, "static", item_image)
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except Exception as img_error:
                    current_app.logger.warning(f"Erro ao remover imagem: {str(img_error)}")
            
            # 5. Registrar ação
            log_action(
                'Exclusão de Item de Estoque',
                'stock_item', 
                id,
                f"Item {item_name} excluído do estoque"
            )
            
            flash('Item excluído com sucesso!', 'success')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao excluir item de estoque: {str(e)}")
            flash(f'Erro ao excluir item: {str(e)}', 'danger')
        
        return redirect(url_for('stock_items'))
        
    @app.route('/estoque/movimentacao', methods=['POST'])
    @login_required
    def add_stock_movement():
        form = StockMovementForm()
        
        if form.validate_on_submit():
            try:
                item = StockItem.query.get_or_404(form.stock_item_id.data)
                
                # Determinar a quantidade (positiva para entrada, negativa para saída)
                quantity = form.quantity.data
                if form.direction.data == 'saida':
                    quantity = -quantity
                
                # Verificar se há quantidade suficiente em caso de saída
                if quantity < 0 and abs(quantity) > item.quantity:
                    flash('Quantidade insuficiente em estoque para esta saída.', 'danger')
                    return redirect(url_for('view_stock_item', id=item.id))
                
                # Criar o movimento
                movement = StockMovement(
                    stock_item_id=form.stock_item_id.data,
                    quantity=quantity,
                    description=form.description.data,
                    reference=form.reference.data,
                    service_order_id=form.service_order_id.data if form.service_order_id.data != 0 else None,
                    created_by=current_user.id
                )
                
                # Atualizar a quantidade do item
                item.quantity += quantity
                
                # Atualizar o status do item
                item.update_status()
                
                db.session.add(movement)
                db.session.commit()
                
                # Registrar a ação
                log_action(
                    f"{'Entrada' if quantity > 0 else 'Saída'} de Estoque",
                    'stock_movement',
                    movement.id,
                    f"{abs(quantity)} unidade(s) {form.direction.data} de {item.name}"
                )
                
                flash('Movimento de estoque registrado com sucesso!', 'success')
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erro ao registrar movimento de estoque: {str(e)}")
                flash(f'Erro ao registrar movimento: {str(e)}', 'danger')
        
        # Redirecionar para a visualização do item
        return redirect(url_for('view_stock_item', id=form.stock_item_id.data))
        
    @app.route('/api/estoque/movimentacao', methods=['POST'])
    @login_required
    def add_stock_movement_ajax():
        """Endpoint para registrar movimento de estoque via AJAX"""
        try:
            # Obter dados do formulário
            stock_item_id = request.form.get('stock_item_id')
            quantity = int(request.form.get('quantity', 1))
            direction = request.form.get('direction')
            description = request.form.get('description', '')
            reference = request.form.get('reference', '')
            
            if not stock_item_id or not direction or not description:
                return jsonify({
                    'success': False, 
                    'message': 'Dados incompletos. Preencha todos os campos obrigatórios.'
                })
            
            # Buscar o item de estoque
            item = StockItem.query.get_or_404(stock_item_id)
            
            # Determinar a quantidade (positiva para entrada, negativa para saída)
            actual_quantity = quantity
            if direction == 'saida':
                actual_quantity = -quantity
            
            # Verificar se há quantidade suficiente em caso de saída
            if actual_quantity < 0 and abs(actual_quantity) > item.quantity:
                return jsonify({
                    'success': False,
                    'message': f'Quantidade insuficiente em estoque. Disponível: {item.quantity}'
                })
            
            # Criar o movimento
            movement = StockMovement(
                stock_item_id=stock_item_id,
                quantity=actual_quantity,
                description=description,
                reference=reference,
                created_by=current_user.id
            )
            
            # Atualizar a quantidade do item
            item.quantity += actual_quantity
            
            # Atualizar o status do item
            item.update_status()
            
            db.session.add(movement)
            db.session.commit()
            
            # Registrar a ação
            action_type = "Entrada" if actual_quantity > 0 else "Saída"
            log_action(
                f"{action_type} de Estoque",
                'stock_movement',
                movement.id,
                f"{abs(actual_quantity)} unidade(s) {direction} de {item.name}"
            )
            
            return jsonify({
                'success': True,
                'message': f'Movimento de {abs(actual_quantity)} unidade(s) registrado com sucesso!',
                'new_quantity': item.quantity,
                'item_id': item.id
            })
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erro ao registrar movimento via AJAX: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Erro ao processar: {str(e)}'
            })

    # Initialize the first admin user if no users exist
    def create_initial_admin():
        # Verificar se a tabela de usuários existe
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if not inspector.has_table('user'):
            return

        # Verificar se a coluna username existe
        columns = [c['name'] for c in inspector.get_columns('user')]
        if 'username' not in columns:
            print("Coluna username não existe. Migrando o banco de dados...")
            # A coluna username não existe, então precisamos criar o esquema do zero
            db.drop_all()
            db.create_all()
            
        # Criar o admin se não houver usuários
        if User.query.count() == 0:
            admin = User(
                username='admin',
                name='Administrador',
                email='admin@samape.com',
                role=UserRole.admin,
                active=True
            )
            admin.set_password('admin123')
            
            db.session.add(admin)
            db.session.commit()
            
            print("Admin user created: username=admin, password=admin123")
            
    # Register function to be called with app context in app.py
    app.create_initial_admin = create_initial_admin
    
    @app.route('/criar_dados_teste')
    @login_required
    def criar_dados_teste():
        """Rota temporária para criar dados de teste no sistema."""
        from create_test_data import create_test_data
        
        try:
            result = create_test_data()
            if result:
                flash('Dados de teste criados com sucesso!', 'success')
            else:
                flash('Falha ao criar dados de teste.', 'danger')
        except Exception as e:
            app.logger.error(f'Erro ao criar dados de teste: {str(e)}')
            flash(f'Erro ao criar dados de teste: {str(e)}', 'danger')
            
        return redirect(url_for('dashboard'))
        
    # Rotas para Controle de Frota
    @app.route('/frota')
    @login_required
    def fleet():
        """Lista de veículos da frota"""
        try:
            # Adicionar logging
            app.logger.info("Acessando página de frota")
            
            # Contador de estatísticas
            stats = {
                'active': Vehicle.query.filter_by(status=VehicleStatus.ativo).count(),
                'maintenance': Vehicle.query.filter_by(status=VehicleStatus.em_manutencao).count(),
                'inactive': Vehicle.query.filter_by(status=VehicleStatus.inativo).count(),
                'total': Vehicle.query.count()
            }
            
            # Inicializar variáveis com valores padrão
            page = request.args.get('page', 1, type=int)
            per_page = int(get_system_setting('items_per_page', '20'))
            
            today = datetime.now().date()
            
            app.logger.info("Preparando query para lista de veículos")
            
            # Query base
            query = Vehicle.query
            
            # Aplicar filtros
            status_filter = request.args.get('status')
            tipo_filter = request.args.get('tipo')
            busca = request.args.get('busca')
            
            if status_filter:
                app.logger.info(f"Aplicando filtro por status: {status_filter}")
                query = query.filter(Vehicle.status == VehicleStatus[status_filter])
                
            if tipo_filter:
                # Filtro de tipo removido - campo não existe na tabela
                app.logger.info(f"Filtro por tipo ignorado (campo não existe): {tipo_filter}")
                pass
                
            if busca:
                app.logger.info(f"Aplicando busca: {busca}")
                query = query.filter(
                    or_(
                        Vehicle.plate.ilike(f'%{busca}%'),
                        Vehicle.brand.ilike(f'%{busca}%'),
                        Vehicle.model.ilike(f'%{busca}%'),
                        Vehicle.chassis.ilike(f'%{busca}%')
                    )
                )
            
            # Ordenação
            order_by = request.args.get('order_by', 'plate')
            order_dir = request.args.get('order_dir', 'asc')
            app.logger.info(f"Ordenando por: {order_by} ({order_dir})")
            
            if order_by == 'plate':
                if order_dir == 'asc':
                    query = query.order_by(Vehicle.plate)
                else:
                    query = query.order_by(Vehicle.plate.desc())
            elif order_by == 'type':
                if order_dir == 'asc':
                    # Ordenação por tipo removida - campo não existe na tabela
                    query = query.order_by(Vehicle.brand)
                else:
                    # Ordenação por tipo removida - campo não existe na tabela
                    query = query.order_by(Vehicle.brand.desc())
            elif order_by == 'status':
                if order_dir == 'asc':
                    query = query.order_by(Vehicle.status)
                else:
                    query = query.order_by(Vehicle.status.desc())
            elif order_by == 'brand':
                if order_dir == 'asc':
                    query = query.order_by(Vehicle.brand)
                else:
                    query = query.order_by(Vehicle.brand.desc())
            else:
                query = query.order_by(Vehicle.plate)
            
            # Paginação
            app.logger.info(f"Aplicando paginação: página {page}, {per_page} itens por página")
            vehicles = query.paginate(page=page, per_page=per_page)
            
            # Obter as últimas movimentações (manutenções e abastecimentos)
            app.logger.info("Buscando últimas movimentações (manutenções e abastecimentos)")
            
            try:
                # Consulta para manutenções
                maintenance_records = db.session.query(
                    VehicleMaintenance.id.label('record_id'),
                    VehicleMaintenance.vehicle_id,
                    VehicleMaintenance.date,
                    VehicleMaintenance.description,
                    VehicleMaintenance.cost,
                    VehicleMaintenance.created_at,
                    db.literal('maintenance').label('record_type')
                ).order_by(VehicleMaintenance.created_at.desc()).limit(5).all()
                
                # Consulta para abastecimentos
                refueling_records = db.session.query(
                    Refueling.id.label('record_id'),
                    Refueling.vehicle_id,
                    Refueling.date,
                    db.literal('Abastecimento').label('description'),
                    Refueling.total_cost.label('cost'),
                    Refueling.created_at,
                    db.literal('refueling').label('record_type')
                ).order_by(Refueling.created_at.desc()).limit(5).all()
                
                # Combinar resultados e ordenar por data de criação
                latest_records = sorted(
                    maintenance_records + refueling_records,
                    key=lambda x: x.created_at,
                    reverse=True
                )[:10]  # Limitar a 10 registros
                
                # Obter informações dos veículos associados
                for record in latest_records:
                    vehicle = Vehicle.query.get(record.vehicle_id)
                    if vehicle:
                        setattr(record, 'vehicle', vehicle)
            except Exception as e:
                app.logger.error(f"Erro ao buscar movimentações recentes: {str(e)}")
                latest_records = []
            
            app.logger.info(f"Renderizando template com {vehicles.total} veículos e {len(latest_records)} movimentações recentes")
            
            return render_template(
                'fleet/index.html',
                vehicles=vehicles,
                status_filter=status_filter,
                tipo_filter=tipo_filter,
                busca=busca,
                order_by=order_by,
                order_dir=order_dir,
                vehicle_statuses=VehicleStatus,
                today=today,
                stats=stats,
                latest_records=latest_records
            )
        except Exception as e:
            app.logger.error(f"Erro ao acessar página de frota: {str(e)}")
            import traceback
            app.logger.error(traceback.format_exc())
            flash(f"Erro ao carregar página de frota: {str(e)}", "danger")
            return redirect(url_for('dashboard'))
        
    @app.route('/frota/novo', methods=['GET', 'POST'])
    @login_required
    @manager_required
    def new_vehicle():
        """Adicionar novo veículo à frota"""
        form = VehicleForm()
        
        if form.validate_on_submit():
            try:
                # Tratar datas
                acquisition_date = None
                if form.acquisition_date.data:
                    acquisition_date = datetime.strptime(form.acquisition_date.data, '%Y-%m-%d').date()
                
                insurance_expiry = None
                if form.insurance_expiry.data:
                    insurance_expiry = datetime.strptime(form.insurance_expiry.data, '%Y-%m-%d').date()
                
                next_maintenance_date = None
                if form.next_maintenance_date.data:
                    next_maintenance_date = datetime.strptime(form.next_maintenance_date.data, '%Y-%m-%d').date()
                
                # Processar imagem, se houver
                image_filename = None
                if form.image.data:
                    image = form.image.data
                    
                    # Gerar nome de arquivo único
                    filename = secure_filename(f"vehicle_{uuid.uuid4().hex}.{image.filename.split('.')[-1]}")
                    upload_folder = os.path.join('static', 'uploads', 'vehicles')
                    os.makedirs(upload_folder, exist_ok=True)
                    image.save(os.path.join(upload_folder, filename))
                    image_filename = filename
                
                # Criar objeto de veículo
                vehicle = Vehicle(
                    # Não adicionar campo type - não existe no banco de dados
                    plate=form.plate.data,
                    brand=form.brand.data,
                    model=form.model.data,
                    year=form.year.data,
                    color=form.color.data,
                    chassis=form.chassis.data,
                    renavam=form.renavam.data,
                    fuel_type=FuelType.flex if not form.fuel_type.data else 
                       FuelType[form.fuel_type.data] if form.fuel_type.data in [fuel_type.name for fuel_type in FuelType] else FuelType.flex,
                    acquisition_date=acquisition_date,
                    insurance_policy=form.insurance_policy.data,
                    insurance_expiry=insurance_expiry,
                    current_km=form.current_km.data,
                    next_maintenance_date=next_maintenance_date,
                    next_maintenance_km=form.next_maintenance_km.data,
                    responsible_id=form.responsible_id.data if form.responsible_id.data != 0 else None,
                    status=VehicleStatus[form.status.data],
                    image=image_filename,
                    notes=form.notes.data
                )
                
                db.session.add(vehicle)
                db.session.commit()
                
                flash('Veículo adicionado com sucesso!', 'success')
                log_action(
                    'Cadastro de Veículo',
                    'vehicle',
                    vehicle.id,
                    f"Veículo placa {vehicle.plate} cadastrado"
                )
                
                return redirect(url_for('view_vehicle', id=vehicle.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao adicionar veículo: {str(e)}', 'danger')
                app.logger.error(f"Erro ao cadastrar veículo: {str(e)}")
        
        return render_template('fleet/new.html', form=form)
        
    @app.route('/frota/<int:id>')
    @login_required
    def view_vehicle(id):
        """Visualizar detalhes de um veículo"""
        vehicle = Vehicle.query.get_or_404(id)
        
        # Obter histórico de manutenção
        maintenance_history = VehicleMaintenance.query.filter_by(vehicle_id=vehicle.id).order_by(VehicleMaintenance.date.desc()).all()
        
        # Obter histórico de abastecimento
        refueling_history = Refueling.query.filter_by(vehicle_id=vehicle.id).order_by(Refueling.date.desc()).all()
        
        # Data atual para o modal de abastecimento
        now_date = datetime.now().strftime('%Y-%m-%d')
        
        return render_template(
            'fleet/view.html',
            vehicle=vehicle,
            maintenance_history=maintenance_history,
            refueling_history=refueling_history,
            now_date=now_date
        )
        
    @app.route('/frota/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    @manager_required
    def edit_vehicle(id):
        """Editar veículo"""
        vehicle = Vehicle.query.get_or_404(id)
        form = VehicleForm(obj=vehicle)
        
        if request.method == 'GET':
            # Converter datas para o formato correto para o formulário
            if vehicle.acquisition_date:
                form.acquisition_date.data = vehicle.acquisition_date.strftime('%Y-%m-%d')
            if vehicle.insurance_expiry:
                form.insurance_expiry.data = vehicle.insurance_expiry.strftime('%Y-%m-%d')
            if vehicle.next_maintenance_date:
                form.next_maintenance_date.data = vehicle.next_maintenance_date.strftime('%Y-%m-%d')
                
            # Lidar com dados do enum
            # type removido - campo não existe no banco de dados
            form.status.data = vehicle.status.name
            
            # Definir responsável
            if vehicle.responsible_id is None:
                form.responsible_id.data = 0
        
        if form.validate_on_submit():
            try:
                # Tratar datas
                acquisition_date = None
                if form.acquisition_date.data:
                    acquisition_date = datetime.strptime(form.acquisition_date.data, '%Y-%m-%d').date()
                
                insurance_expiry = None
                if form.insurance_expiry.data:
                    insurance_expiry = datetime.strptime(form.insurance_expiry.data, '%Y-%m-%d').date()
                
                next_maintenance_date = None
                if form.next_maintenance_date.data:
                    next_maintenance_date = datetime.strptime(form.next_maintenance_date.data, '%Y-%m-%d').date()
                
                # Processar imagem, se houver
                if form.image.data:
                    # Remover imagem anterior se existir
                    if vehicle.image:
                        try:
                            old_image_path = os.path.join('static', 'uploads', 'vehicles', vehicle.image)
                            if os.path.exists(old_image_path):
                                os.remove(old_image_path)
                        except Exception as e:
                            app.logger.warning(f"Erro ao remover imagem antiga: {str(e)}")
                    
                    image = form.image.data
                    
                    # Gerar nome de arquivo único
                    filename = secure_filename(f"vehicle_{uuid.uuid4().hex}.{image.filename.split('.')[-1]}")
                    upload_folder = os.path.join('static', 'uploads', 'vehicles')
                    os.makedirs(upload_folder, exist_ok=True)
                    image.save(os.path.join(upload_folder, filename))
                    vehicle.image = filename
                
                # Atualizar campos do veículo
                # type removido - campo não existe no banco de dados
                vehicle.plate = form.plate.data
                vehicle.brand = form.brand.data
                vehicle.model = form.model.data
                vehicle.year = form.year.data
                vehicle.color = form.color.data
                vehicle.chassis = form.chassis.data
                vehicle.renavam = form.renavam.data
                vehicle.acquisition_date = acquisition_date
                # Tratar o tipo de combustível corretamente
                try:
                    if form.fuel_type.data:
                        # Verificar se o valor está entre os valores válidos do enum
                        valid_fuel_types = [fuel_type.name for fuel_type in FuelType]
                        if form.fuel_type.data in valid_fuel_types:
                            vehicle.fuel_type = FuelType[form.fuel_type.data]
                        else:
                            # Valor padrão se não for um tipo válido
                            vehicle.fuel_type = FuelType.flex
                    else:
                        vehicle.fuel_type = FuelType.flex
                except Exception as e:
                    # Em caso de erro, use um valor padrão
                    app.logger.error(f"Erro ao definir tipo de combustível: {str(e)}")
                    vehicle.fuel_type = FuelType.flex
                vehicle.insurance_policy = form.insurance_policy.data
                vehicle.insurance_expiry = insurance_expiry
                vehicle.current_km = form.current_km.data
                vehicle.next_maintenance_km = form.next_maintenance_km.data
                vehicle.next_maintenance_date = next_maintenance_date
                vehicle.responsible_id = form.responsible_id.data if form.responsible_id.data != 0 else None
                vehicle.status = VehicleStatus[form.status.data]
                vehicle.notes = form.notes.data
                
                db.session.commit()
                
                flash('Veículo atualizado com sucesso!', 'success')
                log_action(
                    'Edição de Veículo',
                    'vehicle',
                    vehicle.id,
                    f"Veículo placa {vehicle.plate} atualizado"
                )
                
                return redirect(url_for('view_vehicle', id=vehicle.id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao atualizar veículo: {str(e)}', 'danger')
                app.logger.error(f"Erro ao atualizar veículo {id}: {str(e)}")
        
        return render_template('fleet/edit.html', form=form, vehicle=vehicle)
        
    @app.route('/frota/<int:id>/excluir', methods=['GET', 'POST'])
    @login_required
    # Removida restrição @role_required para permitir acesso a todos os usuários logados
    def delete_vehicle(id):
        """Excluir veículo - redirecionar para a versão correta"""
        # Redirecionar para a nova rota de exclusão de veículos
        return redirect(url_for('delete_fleet_vehicle', id=id))
        
    @app.route('/frota/<int:id>/manutencao/nova', methods=['GET', 'POST'])
    @login_required
    # Removida restrição @manager_required para permitir acesso a todos os usuários logados
    def new_vehicle_maintenance(id):
        """Registrar nova manutenção para um veículo"""
        vehicle = Vehicle.query.get_or_404(id)
        form = VehicleMaintenanceForm()
        
        # Pré-selecionar o veículo
        form.vehicle_id.data = vehicle.id
        
        # Passar o veículo para o template
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Adicionar log para debug
        app.logger.info(f"Nova manutenção - método: {request.method}")
        
        if request.method == 'POST':
            app.logger.info(f"Form data: {request.form}")
            app.logger.info(f"Form errors: {form.errors}")
            app.logger.info(f"Form válido: {form.validate()}")
        
        if form.validate_on_submit():
            app.logger.info("Formulário válido, iniciando processamento")
            try:
                # Garantir que a data seja um objeto datetime
                maintenance_date = datetime.now()
                if form.date.data:
                    try:
                        if isinstance(form.date.data, str):
                            maintenance_date = datetime.strptime(form.date.data, '%Y-%m-%d')
                        else:
                            maintenance_date = form.date.data
                        app.logger.info(f"Data de manutenção: {maintenance_date}")
                    except Exception as err:
                        app.logger.error(f"Erro ao converter data: {err}, usando data atual")
                
                # Garantir que performed_by_id seja um inteiro ou None
                performed_by = current_user.id
                if form.performed_by_id.data and form.performed_by_id.data != "0":
                    try:
                        performed_by = int(form.performed_by_id.data)
                    except (ValueError, TypeError):
                        pass
                app.logger.info(f"Responsável pela manutenção: {performed_by}")
                
                # Extrair e validar campos do formulário
                description = form.description.data or "Manutenção não especificada"
                mileage = form.mileage.data or 0
                cost = form.cost.data or 0.0
                workshop = form.service_provider.data or ""
                invoice_number = form.invoice_number.data or ""
                
                app.logger.info(f"Dados do formulário processados: descrição='{description}', km={mileage}, custo={cost}")
                
                # Criar objeto de manutenção
                maintenance = VehicleMaintenance()
                maintenance.vehicle_id = vehicle.id
                maintenance.date = maintenance_date
                maintenance.odometer = mileage
                maintenance.description = description
                maintenance.cost = cost
                maintenance.workshop = workshop
                maintenance.invoice_number = invoice_number
                maintenance.created_by = performed_by
                
                app.logger.info(f"Objeto manutenção pronto para inserção: {maintenance}")
                db.session.add(maintenance)
                
                # Atualizar hodômetro do veículo se o valor informado é maior que o atual
                if mileage > 0 and (vehicle.current_km is None or mileage > vehicle.current_km):
                    vehicle.current_km = mileage
                    app.logger.info(f"Atualizando hodômetro do veículo para: {mileage}")
                
                # Usar flush para obter o ID da manutenção sem confirmar a transação
                db.session.flush()
                app.logger.info(f"Manutenção ID após flush: {maintenance.id}")
                
                # Criar entrada financeira se houver custo
                if cost > 0:
                    financial_entry = FinancialEntry()
                    financial_entry.description = f"Manutenção do veículo placa {vehicle.plate} - {description[:50]}"
                    financial_entry.amount = cost
                    financial_entry.type = FinancialEntryType.saida
                    financial_entry.date = maintenance_date
                    financial_entry.created_by = current_user.id
                    financial_entry.entry_type = 'vehicle_maintenance'
                    financial_entry.reference_id = maintenance.id
                    
                    db.session.add(financial_entry)
                    app.logger.info(f"Entrada financeira criada: {financial_entry}")
                
                # Confirmar toda a transação de uma vez
                db.session.commit()
                app.logger.info("Transação confirmada com sucesso!")
                
                flash('Manutenção registrada com sucesso!', 'success')
                log_action(
                    'Registro de Manutenção',
                    'vehicle_maintenance',
                    maintenance.id,
                    f"Manutenção registrada para o veículo placa {vehicle.plate}"
                )
                
                return redirect(url_for('view_vehicle', id=vehicle.id))
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Erro ao registrar manutenção: {str(e)}")
                app.logger.exception(e)  # Log do traceback completo
                flash(f'Erro ao registrar manutenção: {str(e)}', 'danger')
        
        return render_template('fleet/new_maintenance.html', form=form, vehicle=vehicle, today=today)
        
    @app.route('/frota/veiculos/<int:id>/excluir', methods=['GET', 'POST'])
    @login_required
    def delete_fleet_vehicle(id):
        """Rota para excluir um veículo da frota (método legado)"""
        # Verificar se o usuário é administrador
        if current_user.role.value != 'admin':
            flash('Acesso negado. Apenas administradores podem excluir veículos.', 'danger')
            return redirect(url_for('fleet'))
            
        app.logger.info(f"Tentando excluir veículo ID: {id} via método legado {request.method}")
        
        # Redirecionar para o novo método de exclusão
        if request.method == 'POST':
            return redirect(url_for('excluir_veiculo_direct', id=id))
        else:
            # Para solicitações GET, apenas redirecionar para a página de frota
            return redirect(url_for('fleet'))
            
    @app.route('/excluir-veiculo/<int:id>', methods=['POST'])
    @login_required
    def excluir_veiculo_direct(id):
        """Rota para excluir veículo - apenas para administradores"""
        # Verificar se o usuário é administrador 
        if current_user.role.value != 'admin':
            flash('Acesso negado. Apenas administradores podem excluir veículos.', 'danger')
            return redirect(url_for('fleet'))
            
        app.logger.info(f"Tentando excluir veículo ID: {id}, usuário: {current_user.username}")
        
        try:
            # Buscar o veículo
            vehicle = Vehicle.query.get_or_404(id)
            vehicle_info = f"{vehicle.plate} ({vehicle.brand} {vehicle.model})"
            
            # Excluir registros relacionados primeiro
            # Manutenções
            VehicleMaintenance.query.filter_by(vehicle_id=id).delete()
            # Abastecimentos
            Refueling.query.filter_by(vehicle_id=id).delete()
            
            # Excluir o veículo
            db.session.delete(vehicle)
            db.session.commit()
            
            # Log da ação
            app.logger.info(f"Veículo {vehicle_info} excluído com sucesso por {current_user.username}")
            flash(f'Veículo {vehicle_info} excluído com sucesso!', 'success')
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erro ao excluir veículo {id}: {str(e)}")
            flash(f'Erro ao excluir o veículo: {str(e)}', 'danger')
            
        return redirect(url_for('fleet'))
    
    @app.route('/frota/veiculos/<int:id>/abastecimento', methods=['GET', 'POST'])
    @login_required
    # Removida a restrição @manager_required para permitir que todos os usuários registrem abastecimentos
    def register_refueling(id):
        """Rota para registrar abastecimento de veículo"""
        vehicle = Vehicle.query.get_or_404(id)
        
        # Estamos usando o formulário diretamente no template ao invés do objeto forms.RefuelingForm
        
        if request.method == 'GET':
            # Pré-preencher o formulário com valores padrão
            current_date = datetime.now().strftime('%Y-%m-%d')
            return render_template('fleet/refueling.html', vehicle=vehicle, today=current_date)
        
        if request.method == 'POST':
            try:
                # Processar dados do formulário
                date_str = request.form.get('date')
                odometer = request.form.get('odometer')
                fuel_type = request.form.get('fuel_type')
                liters = request.form.get('liters')
                price_per_liter = request.form.get('price_per_liter')
                total_cost = request.form.get('total_cost')
                gas_station = request.form.get('gas_station')
                full_tank = 'full_tank' in request.form
                
                # Validar campos obrigatórios
                if not all([date_str, odometer, fuel_type, liters, price_per_liter, total_cost]):
                    flash('Por favor, preencha todos os campos obrigatórios.', 'danger')
                    return render_template('fleet/refueling.html', 
                                          vehicle=vehicle, 
                                          today=date_str or datetime.now().strftime('%Y-%m-%d'))
                
                try:
                    # Converter valores
                    refueling_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    odometer = int(odometer)
                    liters = float(liters)
                    price_per_liter = float(price_per_liter)
                    total_cost = float(total_cost)
                except ValueError as e:
                    flash(f'Erro ao converter valores: {str(e)}', 'danger')
                    return render_template('fleet/refueling.html', 
                                          vehicle=vehicle, 
                                          today=date_str or datetime.now().strftime('%Y-%m-%d'))
                
                # Criar o registro de abastecimento
                # Determinar o tipo de combustível correto
                try:
                    # Converter o tipo de combustível para o enum correto
                    fuel_type_enum = FuelType[fuel_type] if fuel_type in [ft.name for ft in FuelType] else FuelType.flex
                except (KeyError, ValueError):
                    # Fallback para o tipo padrão se houver erro
                    fuel_type_enum = FuelType.flex
                
                refueling = Refueling(
                    vehicle_id=vehicle.id,
                    date=refueling_date,
                    odometer=odometer,
                    fuel_type=fuel_type_enum,  # Usando o enum correto
                    liters=liters,
                    price_per_liter=price_per_liter,
                    total_cost=total_cost,
                    gas_station=gas_station,
                    full_tank=full_tank,
                    created_by=current_user.id
                )
                
                # Atualizar a quilometragem atual do veículo
                if odometer > (vehicle.current_km or 0):
                    vehicle.current_km = odometer
                
                # Primeiro, salvar o registro de abastecimento para obter um ID válido
                db.session.add(refueling)
                db.session.flush()  # Isso gera um ID sem confirmar a transação
                
                # Agora criar lançamento financeiro com o ID correto do abastecimento
                financial_entry = FinancialEntry(
                    date=refueling_date,
                    amount=total_cost,
                    description=f"Abastecimento - {vehicle.brand} {vehicle.model} ({vehicle.plate}) - Combustível",
                    type=FinancialEntryType.saida,
                    created_by=current_user.id,
                    entry_type='vehicle_refueling',
                    reference_id=refueling.id  # Agora o ID é válido
                )
                
                # Adicionar e confirmar a transação
                db.session.add(financial_entry)
                db.session.commit()
                
                # Registrar ação no log
                log_action(
                    'Registro de Abastecimento',
                    'vehicle_refueling',
                    refueling.id,
                    f"Abastecimento registrado para o veículo {vehicle.plate}"
                )
                
                flash(f'Abastecimento registrado com sucesso! Custo total: R$ {total_cost:.2f}', 'success')
                return redirect(url_for('view_vehicle', id=vehicle.id))
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao registrar abastecimento: {str(e)}', 'danger')
                app.logger.error(f"Erro ao registrar abastecimento para veículo {id}: {str(e)}")
                return redirect(url_for('view_vehicle', id=id))
        
        return redirect(url_for('view_vehicle', id=id))
    
    @app.route('/frota/manutencoes')
    @login_required
    def vehicle_maintenance_history():
        """Histórico de manutenções e abastecimentos de todos os veículos"""
        page = request.args.get('page', 1, type=int)
        per_page = int(get_system_setting('items_per_page', '20'))
        view_type = request.args.get('view', 'maintenance')  # 'maintenance' ou 'refueling'
        
        # Obter lista de veículos para o filtro
        vehicles = Vehicle.query.order_by(Vehicle.plate).all()
        
        # Aplicar filtros
        vehicle_id = request.args.get('vehicle_id', type=int)
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        # Converter datas se fornecidas
        inicio_date = None
        fim_date = None
        
        if data_inicio:
            try:
                inicio_date = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            except ValueError:
                flash('Data inicial inválida.', 'warning')
                
        if data_fim:
            try:
                fim_date = datetime.strptime(data_fim, '%Y-%m-%d').date()
            except ValueError:
                flash('Data final inválida.', 'warning')
        
        # Variáveis para os resultados
        maintenance_history = None
        refuelings = None
        
        # Dependendo do tipo de visualização, obtemos manutenções ou abastecimentos
        if view_type != 'refueling':  # Padrão: manutenções
            # Query para manutenções
            query = VehicleMaintenance.query
            
            if vehicle_id:
                query = query.filter(VehicleMaintenance.vehicle_id == vehicle_id)
                
            if inicio_date:
                query = query.filter(VehicleMaintenance.date >= inicio_date)
                
            if fim_date:
                query = query.filter(VehicleMaintenance.date <= fim_date)
            
            # Ordenação por data (coluna real, não propriedade)
            query = query.order_by(VehicleMaintenance.date.desc())
            
            # Paginação
            maintenance_history = query.paginate(page=page, per_page=per_page)
            
        else:  # 'refueling'
            # Query para abastecimentos
            query = Refueling.query
            
            if vehicle_id:
                query = query.filter(Refueling.vehicle_id == vehicle_id)
                
            if inicio_date:
                query = query.filter(Refueling.date >= inicio_date)
                
            if fim_date:
                query = query.filter(Refueling.date <= fim_date)
            
            # Ordenação
            query = query.order_by(Refueling.date.desc())
            
            # Paginação
            refuelings = query.paginate(page=page, per_page=per_page)
        
        # Formatação das datas para o template
        data_inicio_str = data_inicio
        data_fim_str = data_fim
        
        if isinstance(inicio_date, date):
            data_inicio_str = inicio_date.strftime('%Y-%m-%d')
            
        if isinstance(fim_date, date):
            data_fim_str = fim_date.strftime('%Y-%m-%d')
        
        return render_template(
            'fleet/maintenance_history.html',
            maintenance_history=maintenance_history,
            refuelings=refuelings,
            vehicles=vehicles,
            vehicle_id=vehicle_id,
            data_inicio=data_inicio_str,
            data_fim=data_fim_str,
            view_type=view_type
        )
