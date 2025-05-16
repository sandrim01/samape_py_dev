import os
import re
import json
from datetime import datetime
from functools import wraps
from flask import render_template, redirect, url_for, flash, request, jsonify, session, abort
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

    @app.route('/os/<int:id>')
    @login_required
    def view_service_order(id):
        service_order = ServiceOrder.query.get_or_404(id)
        close_form = CloseServiceOrderForm()
        return render_template('service_orders/view.html', service_order=service_order, close_form=close_form)

    @app.route('/os/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    def edit_service_order(id):
        service_order = ServiceOrder.query.get_or_404(id)
        
        # Removida restrição de edição para OS fechadas
        form = ServiceOrderForm(obj=service_order)
        
        # Load clients for dropdown
        form.client_id.choices = [(c.id, c.name) for c in Client.query.order_by(Client.name).all()]
        
        # Load employees for dropdown
        form.responsible_id.choices = [(0, 'A ser definido')] + [
            (u.id, u.name) for u in User.query.filter_by(active=True).order_by(User.name).all()
        ]
        
        # Set initial selection for equipment
        if request.method == 'GET':
            form.equipment_ids.data = ','.join([str(eq.id) for eq in service_order.equipment])
            
            # Handle case where responsible_id is None
            if service_order.responsible_id is None:
                form.responsible_id.data = 0
                
            # Set invoice_amount if OS is closed
            if service_order.status.name == 'fechada' and service_order.invoice_amount:
                form.invoice_amount.data = service_order.invoice_amount
                
        if form.validate_on_submit():
            try:
                # Verifique se estamos alterando o valor da nota de uma OS fechada
                # e armazene o valor antigo para comparação
                old_invoice_amount = None
                if service_order.status.name == 'fechada' and service_order.invoice_amount:
                    old_invoice_amount = service_order.invoice_amount
                
                service_order.client_id = form.client_id.data
                service_order.responsible_id = form.responsible_id.data if form.responsible_id.data != 0 else None
                service_order.description = form.description.data
                service_order.estimated_value = form.estimated_value.data
                service_order.status = ServiceOrderStatus[form.status.data]
                
                # Se a OS está fechada, atualize o valor total da nota
                if service_order.status.name == 'fechada' and form.invoice_amount.data:
                    service_order.invoice_amount = form.invoice_amount.data
                
                # Update equipment relationships
                service_order.equipment = []
                if form.equipment_ids.data:
                    equipment_ids = form.equipment_ids.data.split(',')
                    for eq_id in equipment_ids:
                        equipment = Equipment.query.get(int(eq_id))
                        if equipment and equipment.client_id == service_order.client_id:
                            service_order.equipment.append(equipment)
                
                # Salve as alterações na OS
                db.session.commit()
                
                # Se alteramos o valor da nota e existem lançamentos financeiros relacionados
                # devemos atualizar esses lançamentos
                if (old_invoice_amount is not None and 
                    form.invoice_amount.data is not None and 
                    old_invoice_amount != form.invoice_amount.data):
                    
                    # Busque o lançamento financeiro associado à OS
                    financial_entry = FinancialEntry.query.filter_by(
                        service_order_id=service_order.id,
                        type=FinancialEntryType.entrada
                    ).first()
                    
                    if financial_entry:
                        financial_entry.amount = form.invoice_amount.data
                        financial_entry.description = f"Pagamento OS #{service_order.id} - {service_order.client.name} (Atualizado)"
                        db.session.commit()
                        
                        log_action(
                            'Atualização Financeira',
                            'financial',
                            financial_entry.id,
                            f"Valor da OS #{service_order.id} atualizado de {old_invoice_amount} para {form.invoice_amount.data}"
                        )
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao atualizar OS: {str(e)}', 'danger')
                app.logger.error(f"Erro ao atualizar OS {id}: {str(e)}")
                return redirect(url_for('view_service_order', id=service_order.id))
            
            # Processar imagens - verificar se há arquivos enviados
            image_files = request.files.getlist('images')
            if image_files and any(f.filename for f in image_files):
                saved_images = save_service_order_images(
                    service_order, 
                    image_files, 
                    form.image_descriptions.data
                )
                if saved_images:
                    flash(f'{len(saved_images)} imagem(ns) adicional(is) anexada(s) com sucesso!', 'info')
            
            log_action(
                'Edição de OS',
                'service_order',
                service_order.id,
                f"OS {id} atualizada"
            )
            
            flash('Ordem de serviço atualizada com sucesso!', 'success')
            return redirect(url_for('view_service_order', id=service_order.id))
            
        return render_template(
            'service_orders/edit.html',
            form=form,
            service_order=service_order
        )

    @app.route('/os/imagem/<int:image_id>/excluir', methods=['POST'])
    @login_required
    def delete_service_order_image_route(image_id):
        """Rota para excluir uma imagem de ordem de serviço"""
        # Criar instância do formulário para validação CSRF
        from forms import DeleteImageForm
        form = DeleteImageForm()
        
        # Buscar imagem para obter o service_order_id antes de qualquer validação
        image = ServiceOrderImage.query.get_or_404(image_id)
        service_order_id = image.service_order_id
        
        if form.validate_on_submit():
            # Removida restrição para exclusão de imagens em OS fechadas
            service_order = ServiceOrder.query.get(service_order_id)
            
            # Excluir a imagem
            success, message = delete_service_order_image(image_id)
            
            if success:
                flash('Imagem excluída com sucesso!', 'success')
                log_action(
                    'Exclusão de imagem',
                    'service_order_image',
                    image_id,
                    f"Imagem removida da OS #{service_order_id}"
                )
            else:
                flash(f'Erro ao excluir imagem: {message}', 'danger')
        else:
            # Se falhou na validação CSRF
            flash('Erro de validação do formulário. Tente novamente.', 'danger')
            
        return redirect(url_for('view_service_order', id=service_order_id))
    
    @app.route('/os/<int:id>/fechar', methods=['GET', 'POST'])
    @login_required
    def close_service_order(id):
        service_order = ServiceOrder.query.get_or_404(id)
        
        # Check if order is already closed
        if service_order.status == ServiceOrderStatus.fechada:
            flash('Esta OS já está fechada.', 'warning')
            return redirect(url_for('view_service_order', id=id))
            
        form = CloseServiceOrderForm()
        
        if form.validate_on_submit():
            try:
                # Gerar o número da nota automaticamente
                from utils import get_next_invoice_number
                
                service_order.status = ServiceOrderStatus.fechada
                service_order.closed_at = datetime.utcnow()
                service_order.invoice_number = get_next_invoice_number()
                service_order.invoice_date = datetime.utcnow()
                service_order.invoice_amount = form.invoice_amount.data
                service_order.service_details = form.service_details.data
                
                # Verificamos se o cliente existe antes de tentar criar a entrada financeira
                if not service_order.client:
                    flash('Erro: Cliente não encontrado. Não é possível fechar a OS.', 'danger')
                    return redirect(url_for('view_service_order', id=id))
                
                # Verificar se já existe um lançamento financeiro para esta OS
                existing_entry = FinancialEntry.query.filter_by(
                    service_order_id=service_order.id,
                    type=FinancialEntryType.entrada
                ).first()
                
                # Se já existe, atualiza o valor; senão, cria um novo lançamento
                if existing_entry:
                    existing_entry.amount = form.invoice_amount.data
                    existing_entry.description = f"Pagamento OS #{service_order.id} - {service_order.client.name} (Atualizado)"
                    db.session.commit()
                    
                    log_action(
                        'Atualização Financeira',
                        'financial',
                        existing_entry.id,
                        f"Valor da OS #{service_order.id} atualizado para {form.invoice_amount.data}"
                    )
                else:
                    # Create new financial entry
                    financial_entry = FinancialEntry(
                        service_order_id=service_order.id,
                        description=f"Pagamento OS #{service_order.id} - {service_order.client.name}",
                        amount=form.invoice_amount.data,
                        type=FinancialEntryType.entrada,
                        created_by=current_user.id
                    )
                    
                    db.session.add(financial_entry)
                    db.session.commit()
                
                flash(f'OS #{service_order.id} fechada com sucesso!', 'success')
                log_action(
                    'Fechamento de OS',
                    'service_order',
                    service_order.id,
                    f"OS fechada - Valor: R${form.invoice_amount.data}"
                )
                
                return redirect(url_for('view_service_order', id=id))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao fechar OS: {str(e)}', 'danger')
                app.logger.error(f"Erro ao fechar OS {id}: {str(e)}")
                return redirect(url_for('view_service_order', id=id))
            
        return render_template(
            'service_orders/close.html',
            service_order=service_order,
            form=form
        )
        
    @app.route('/ordem-servico/<int:id>/excluir')
    @login_required
    @admin_required
    def delete_service_order(id):
        """Rota para excluir uma ordem de serviço"""
        try:
            service_order = ServiceOrder.query.get_or_404(id)
            
            # Verificar se há fotos relacionadas
            images = ServiceOrderImage.query.filter_by(service_order_id=id).all()
            for image in images:
                try:
                    # Tenta excluir o arquivo físico
                    file_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), image.filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                except Exception as img_error:
                    app.logger.error(f"Erro ao excluir arquivo de imagem: {str(img_error)}")
                
                db.session.delete(image)
            
            # Remover relações com equipamentos na tabela de relacionamento
            db.session.execute(
                db.delete(equipment_service_orders).where(
                    equipment_service_orders.c.service_order_id == id
                )
            )
            
            # Verificar se há entradas financeiras relacionadas
            financial_entries = FinancialEntry.query.filter_by(service_order_id=id).all()
            for entry in financial_entries:
                db.session.delete(entry)
            
            # Excluir a ordem de serviço
            order_number = service_order.id
            client_name = service_order.client.name if service_order.client else "Cliente desconhecido"
            db.session.delete(service_order)
            db.session.commit()
            
            try:
                log_action(
                    'Exclusão de Ordem de Serviço',
                    'service_order',
                    id,
                    f"OS #{order_number} de {client_name} excluída"
                )
            except Exception as log_error:
                app.logger.error(f"Erro ao registrar log de exclusão de OS: {str(log_error)}")
            
            flash('Ordem de serviço excluída com sucesso!', 'success')
            return redirect(url_for('service_orders'))
            
        except IntegrityError:
            db.session.rollback()
            flash('Erro de integridade ao excluir ordem de serviço. Pode haver registros vinculados.', 'danger')
            return redirect(url_for('view_service_order', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao excluir ordem de serviço: {str(e)}', 'danger')
            app.logger.error(f"Erro ao excluir ordem de serviço {id}: {str(e)}")
            return redirect(url_for('view_service_order', id=id))

    @app.route('/api/cliente/<int:client_id>/equipamentos')
    @login_required
    def get_client_equipment(client_id):
        equipment = Equipment.query.filter_by(client_id=client_id).all()
        return jsonify([{
            'id': eq.id,
            'type': eq.type,
            'brand': eq.brand or '',
            'model': eq.model or '',
            'serial_number': eq.serial_number or ''
        } for eq in equipment])

    # Client routes
    @app.route('/clientes')
    @login_required
    def clients():
        search = request.args.get('search', '')
        
        if search:
            clients = Client.query.filter(
                or_(
                    Client.name.ilike(f'%{search}%'),
                    Client.document.ilike(f'%{search}%')
                )
            ).order_by(Client.name).all()
        else:
            clients = Client.query.order_by(Client.name).all()
            
        return render_template('clients/index.html', clients=clients, search=search)

    @app.route('/clientes/novo', methods=['GET', 'POST'])
    @login_required
    def new_client():
        form = ClientForm()
        
        if form.validate_on_submit():
            try:
                # Remover caracteres especiais do documento
                doc = re.sub(r'[^0-9]', '', form.document.data)
                
                # Verificar se já existe um cliente com este documento
                existing_client = Client.query.filter_by(document=doc).first()
                if existing_client:
                    flash('Já existe um cliente cadastrado com este CPF/CNPJ.', 'danger')
                    return render_template('clients/create.html', form=form)
                
                client = Client(
                    name=form.name.data,
                    document=doc,  # Salvamos apenas os números
                    email=form.email.data,
                    phone=form.phone.data,
                    address=form.address.data
                )
                
                db.session.add(client)
                db.session.commit()
                
                try:
                    log_action(
                        'Criação de Cliente',
                        'client',
                        client.id,
                        f"Cliente {client.name} criado"
                    )
                except Exception:
                    # Se falhar ao registrar o log, não interromper o fluxo principal
                    pass
                
                flash('Cliente cadastrado com sucesso!', 'success')
                return redirect(url_for('clients'))
            except IntegrityError as e:
                db.session.rollback()
                app.logger.error(f"Erro de integridade: {str(e)}")
                flash(f'Erro de integridade ao cadastrar cliente: {str(e)}', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao cadastrar cliente: {str(e)}', 'danger')
            
        return render_template('clients/create.html', form=form)

    @app.route('/clientes/<int:id>')
    @login_required
    def view_client(id):
        client = Client.query.get_or_404(id)
        equipment = Equipment.query.filter_by(client_id=id).all()
        service_orders = ServiceOrder.query.filter_by(client_id=id).order_by(ServiceOrder.created_at.desc()).all()
        
        return render_template(
            'clients/view.html',
            client=client,
            equipment=equipment,
            service_orders=service_orders
        )

    @app.route('/clientes/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    def edit_client(id):
        client = Client.query.get_or_404(id)
        form = ClientForm(obj=client)
        
        # Store client ID for validation
        form.client_id = client.id
        
        if form.validate_on_submit():
            client.name = form.name.data
            # Formatar automaticamente o CPF/CNPJ se foi alterado
            if client.document != form.document.data:
                client.document = identify_and_format_document(form.document.data)
            else:
                client.document = form.document.data
            client.email = form.email.data
            client.phone = form.phone.data
            client.address = form.address.data
            
            db.session.commit()
            
            log_action(
                'Edição de Cliente',
                'client',
                client.id,
                f"Cliente {client.name} atualizado"
            )
            
            flash('Cliente atualizado com sucesso!', 'success')
            return redirect(url_for('view_client', id=id))
            
        return render_template('clients/edit.html', form=form, client=client)

    @app.route('/clientes/<int:id>/excluir', methods=['POST'])
    @admin_required
    def delete_client(id):
        try:
            client = Client.query.get_or_404(id)
            
            # Check if client has service orders
            if ServiceOrder.query.filter_by(client_id=id).count() > 0:
                flash('Não é possível excluir um cliente com ordens de serviço.', 'danger')
                return redirect(url_for('view_client', id=id))
                
            # Check if client has equipment
            if Equipment.query.filter_by(client_id=id).count() > 0:
                flash('Não é possível excluir um cliente com equipamentos. Remova os equipamentos primeiro.', 'danger')
                return redirect(url_for('view_client', id=id))
            
            client_name = client.name
            db.session.delete(client)
            db.session.commit()
            
            try:
                log_action(
                    'Exclusão de Cliente',
                    'client',
                    id,
                    f"Cliente {client_name} excluído"
                )
            except Exception as log_error:
                app.logger.error(f"Erro ao registrar log de exclusão de cliente: {str(log_error)}")
            
            flash('Cliente excluído com sucesso!', 'success')
            return redirect(url_for('clients'))
            
        except IntegrityError:
            db.session.rollback()
            flash('Erro de integridade ao excluir cliente. Pode haver registros vinculados a este cliente.', 'danger')
            return redirect(url_for('view_client', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao excluir cliente: {str(e)}', 'danger')
            app.logger.error(f"Erro ao excluir cliente {id}: {str(e)}")
            return redirect(url_for('view_client', id=id))
            
    @app.route('/admin/clientes/<int:id>/excluir-direto')
    @admin_required
    def delete_client_direct(id):
        """Rota alternativa para exclusão de clientes"""
        try:
            client = Client.query.get_or_404(id)
            
            # Check if client has service orders
            if ServiceOrder.query.filter_by(client_id=id).count() > 0:
                flash('Não é possível excluir um cliente com ordens de serviço.', 'danger')
                return redirect(url_for('view_client', id=id))
                
            # Check if client has equipment
            if Equipment.query.filter_by(client_id=id).count() > 0:
                flash('Não é possível excluir um cliente com equipamentos. Remova os equipamentos primeiro.', 'danger')
                return redirect(url_for('view_client', id=id))
            
            client_name = client.name
            db.session.delete(client)
            db.session.commit()
            
            try:
                log_action(
                    'Exclusão de Cliente',
                    'client',
                    id,
                    f"Cliente {client_name} excluído"
                )
            except Exception as log_error:
                app.logger.error(f"Erro ao registrar log de exclusão de cliente: {str(log_error)}")
            
            flash('Cliente excluído com sucesso!', 'success')
            return redirect(url_for('clients'))
            
        except IntegrityError:
            db.session.rollback()
            flash('Erro de integridade ao excluir cliente. Pode haver registros vinculados a este cliente.', 'danger')
            return redirect(url_for('view_client', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao excluir cliente: {str(e)}', 'danger')
            app.logger.error(f"Erro ao excluir cliente {id}: {str(e)}")
            return redirect(url_for('view_client', id=id))

    # Equipment API endpoints
    @app.route('/api/equipamentos/modelos-por-marca', methods=['GET'])
    @login_required
    def get_models_by_brand():
        """
        Retorna os modelos disponíveis para uma marca específica
        Utilizado para o preenchimento dinâmico do campo de modelo no formulário de equipamento
        """
        brand = request.args.get('brand', '')
        
        if not brand:
            return jsonify([])
        
        # Buscar modelos distintos para a marca selecionada
        from sqlalchemy import distinct
        models = db.session.query(distinct(Equipment.model))\
            .filter(Equipment.brand == brand)\
            .order_by(Equipment.model)\
            .all()
        
        # Formatar para retornar como JSON
        model_list = [{'value': m[0], 'text': m[0]} for m in models if m[0]]
        
        return jsonify(model_list)
    
    # Equipment routes
    @app.route('/maquinarios')
    @login_required
    def equipment():
        client_id = request.args.get('client_id', type=int)
        search = request.args.get('search', '')
        
        query = Equipment.query
        
        if client_id:
            query = query.filter_by(client_id=client_id)
            
        if search:
            query = query.filter(
                or_(
                    Equipment.type.ilike(f'%{search}%'),
                    Equipment.brand.ilike(f'%{search}%'),
                    Equipment.model.ilike(f'%{search}%'),
                    Equipment.serial_number.ilike(f'%{search}%')
                )
            )
            
        equipment_list = query.order_by(Equipment.client_id, Equipment.type).all()
        clients = Client.query.order_by(Client.name).all()
        
        return render_template(
            'equipment/index.html',
            equipment=equipment_list,
            clients=clients,
            client_id=client_id,
            search=search
        )

    @app.route('/maquinarios/novo', methods=['GET', 'POST'])
    @login_required
    def new_equipment():
        form = EquipmentForm()
        
        # Load clients for dropdown
        form.client_id.choices = [(c.id, c.name) for c in Client.query.order_by(Client.name).all()]
        
        if form.validate_on_submit():
            try:
                # Usar o valor do select se estiver preenchido, caso contrário usar o valor do campo texto
                equipment_type = form.type_select.data if form.type_select.data else form.type.data
                equipment_brand = form.brand_select.data if form.brand_select.data else form.brand.data
                equipment_model = form.model_select.data if form.model_select.data else form.model.data
                
                # Verificar se todos os campos necessários estão preenchidos
                if not equipment_type:
                    flash('Tipo de equipamento é obrigatório. Selecione um tipo ou preencha o campo "Outro Tipo".', 'danger')
                    return render_template('equipment/create.html', form=form)
                
                equipment = Equipment(
                    client_id=form.client_id.data,
                    type=equipment_type,
                    brand=equipment_brand,
                    model=equipment_model,
                    serial_number=form.serial_number.data,
                    year=form.year.data
                )
                
                db.session.add(equipment)
                db.session.commit()
                
                try:
                    log_action(
                        'Criação de Equipamento',
                        'equipment',
                        equipment.id,
                        f"Equipamento {equipment.type} {equipment.brand} {equipment.model} criado para cliente {equipment.client.name}"
                    )
                except Exception:
                    # Se falhar ao registrar o log, não interromper o fluxo principal
                    pass
                
                flash('Equipamento cadastrado com sucesso!', 'success')
                return redirect(url_for('equipment'))
            except IntegrityError:
                db.session.rollback()
                flash('Erro de integridade ao criar o equipamento. O ID pode estar duplicado.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao cadastrar equipamento: {str(e)}', 'danger')
            
        # Pre-fill client_id if provided in query string
        client_id = request.args.get('client_id', type=int)
        if client_id:
            form.client_id.data = client_id
            
        return render_template('equipment/create.html', form=form)

    @app.route('/maquinarios/<int:id>')
    @login_required
    def view_equipment(id):
        equipment = Equipment.query.get_or_404(id)
        service_orders = equipment.service_orders
        form = FlaskForm()  # Formulário vazio apenas para o token CSRF
        
        return render_template(
            'equipment/view.html',
            equipment=equipment,
            service_orders=service_orders,
            form=form
        )

    @app.route('/maquinarios/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    def edit_equipment(id):
        equipment = Equipment.query.get_or_404(id)
        form = EquipmentForm()
        
        # Load clients for dropdown
        form.client_id.choices = [(c.id, c.name) for c in Client.query.order_by(Client.name).all()]
        
        # Adicionar os valores atuais do equipamento às listas de seleção se não estiverem presentes
        from sqlalchemy import distinct
        
        # Se o tipo do equipamento não estiver nas opções, adicionar
        types = [choice[0] for choice in form.type_select.choices if choice[0]]
        if equipment.type and equipment.type not in types:
            form.type_select.choices.append((equipment.type, equipment.type))
            
        # Se a marca do equipamento não estiver nas opções, adicionar
        brands = [choice[0] for choice in form.brand_select.choices if choice[0]]
        if equipment.brand and equipment.brand not in brands:
            form.brand_select.choices.append((equipment.brand, equipment.brand))
            
        # Adicionar modelos da marca atual para o campo model_select
        if equipment.brand:
            models = db.session.query(distinct(Equipment.model))\
                .filter(Equipment.brand == equipment.brand)\
                .order_by(Equipment.model)\
                .all()
            model_choices = [('', 'Selecione um modelo')] + [(m[0], m[0]) for m in models if m[0]]
            form.model_select.choices = model_choices
            
        # Preencher o formulário na primeira vez
        if request.method == 'GET':
            form.client_id.data = equipment.client_id
            
            # Preencher os campos de seleção, se possível
            if equipment.type:
                form.type_select.data = equipment.type
            else:
                form.type.data = equipment.type
                
            if equipment.brand:
                form.brand_select.data = equipment.brand
            else:
                form.brand.data = equipment.brand
                
            if equipment.model:
                # Adicionar o modelo atual às opções se ainda não estiver presente
                model_values = [choice[0] for choice in form.model_select.choices]
                if equipment.model not in model_values and equipment.model:
                    form.model_select.choices.append((equipment.model, equipment.model))
                form.model_select.data = equipment.model
            else:
                form.model.data = equipment.model
                
            form.serial_number.data = equipment.serial_number
            form.year.data = equipment.year
        
        if form.validate_on_submit():
            equipment.client_id = form.client_id.data
            
            # Processar o tipo (usar o campo de texto se 'outro' for selecionado)
            if form.type_select.data == 'outro':
                equipment.type = form.type.data
            else:
                equipment.type = form.type_select.data
                
            # Processar a marca (usar o campo de texto se 'outro' for selecionado)
            if form.brand_select.data == 'outro':
                equipment.brand = form.brand.data
            else:
                equipment.brand = form.brand_select.data
                
            # Processar o modelo (usar o campo de texto se 'outro' for selecionado)
            if form.model_select.data == 'outro':
                equipment.model = form.model.data
            else:
                equipment.model = form.model_select.data
                
            equipment.serial_number = form.serial_number.data
            equipment.year = form.year.data
            
            db.session.commit()
            
            log_action(
                'Edição de Equipamento',
                'equipment',
                equipment.id,
                f"Equipamento {equipment.type} {equipment.brand} {equipment.model} atualizado"
            )
            
            flash('Equipamento atualizado com sucesso!', 'success')
            return redirect(url_for('view_equipment', id=id))
            
        return render_template('equipment/edit.html', form=form, equipment=equipment)

    @app.route('/maquinarios/<int:id>/excluir', methods=['POST'])
    @login_required
    def delete_equipment(id):
        equipment = Equipment.query.get_or_404(id)
        
        # Check if equipment is used in any service order
        if equipment.service_orders:
            flash('Não é possível excluir um equipamento associado a ordens de serviço.', 'danger')
            return redirect(url_for('view_equipment', id=id))
            
        equipment_type = equipment.type
        client_name = equipment.client.name
        db.session.delete(equipment)
        db.session.commit()
        
        log_action(
            'Exclusão de Equipamento',
            'equipment',
            id,
            f"Equipamento {equipment_type} do cliente {client_name} excluído"
        )
        
        flash('Equipamento excluído com sucesso!', 'success')
        return redirect(url_for('equipment'))

    # Service Order Image route
    @app.route('/imagem_os/<int:image_id>')
    @login_required
    def view_service_order_image(image_id):
        """Rota para visualizar uma imagem de ordem de serviço"""
        image = ServiceOrderImage.query.get_or_404(image_id)
        
        # Verificar se o arquivo existe
        file_path = os.path.join(current_app.static_folder, image.filename)
        if not os.path.exists(file_path):
            # Se o arquivo não existir, exibir uma imagem padrão
            return redirect(url_for('static', filename='img/image-not-found.svg'))
            
        return redirect(url_for('static', filename=image.filename))
    
    # Employee routes
    @app.route('/funcionarios')
    @manager_required
    def employees():
        employees = User.query.order_by(User.name).all()
        return render_template('employees/index.html', employees=employees)

    @app.route('/funcionarios/novo', methods=['GET', 'POST'])
    @admin_required
    def new_employee():
        form = UserForm()
        
        if form.validate_on_submit():
            user = User(
                username=form.username.data,
                name=form.name.data,
                email=form.email.data,
                role=UserRole[form.role.data],
                active=form.active.data
            )
            
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            log_action(
                'Criação de Funcionário',
                'user',
                user.id,
                f"Funcionário {user.name} criado com papel {user.role.value}"
            )
            
            flash('Funcionário cadastrado com sucesso!', 'success')
            return redirect(url_for('employees'))
            
        return render_template('employees/create.html', form=form)

    @app.route('/funcionarios/<int:id>/editar', methods=['GET', 'POST'])
    @admin_required
    def edit_employee(id):
        user = User.query.get_or_404(id)
        form = UserForm(obj=user)
        
        # Store user ID for validation
        form.user_id = user.id
        
        # Remove password requirement for existing users
        form.password.validators = [Optional()]
        
        if form.validate_on_submit():
            user.username = form.username.data
            user.name = form.name.data
            user.email = form.email.data
            user.role = UserRole[form.role.data]
            user.active = form.active.data
            
            # Update password only if provided
            if form.password.data:
                user.set_password(form.password.data)
                
            db.session.commit()
            
            log_action(
                'Edição de Funcionário',
                'user',
                user.id,
                f"Funcionário {user.name} atualizado com papel {user.role.value}"
            )
            
            flash('Funcionário atualizado com sucesso!', 'success')
            return redirect(url_for('employees'))
            
        return render_template('employees/edit.html', form=form, user=user)

    @app.route('/funcionarios/<int:id>/ativar', methods=['POST'])
    @admin_required
    def toggle_employee_status(id):
        user = User.query.get_or_404(id)
        
        # Prevent deactivating yourself
        if user.id == current_user.id:
            flash('Você não pode desativar sua própria conta.', 'danger')
            return redirect(url_for('employees'))
            
        user.active = not user.active
        action = 'ativado' if user.active else 'desativado'
        
        db.session.commit()
        
        log_action(
            f'Funcionário {action}',
            'user',
            user.id,
            f"Funcionário {user.name} foi {action}"
        )
        
        flash(f'Funcionário {action} com sucesso!', 'success')
        return redirect(url_for('employees'))

    # Financial routes
    @app.route('/financeiro')
    @manager_required
    def financial():
        month = request.args.get('month', datetime.utcnow().month, type=int)
        year = request.args.get('year', datetime.utcnow().year, type=int)
        
        # Get entries for the selected month
        entries = FinancialEntry.query.filter(
            func.extract('month', FinancialEntry.date) == month,
            func.extract('year', FinancialEntry.date) == year
        ).order_by(FinancialEntry.date.desc()).all()
        
        # Calculate summary
        income = sum(e.amount for e in entries if e.type == FinancialEntryType.entrada)
        expenses = sum(e.amount for e in entries if e.type == FinancialEntryType.saida)
        balance = income - expenses
        
        return render_template(
            'financial/index.html',
            entries=entries,
            month=month,
            year=year,
            income=income,
            expenses=expenses,
            balance=balance
        )

    @app.route('/financeiro/novo', methods=['GET', 'POST'])
    @manager_required
    def new_financial_entry():
        form = FinancialEntryForm()
        
        # Load service orders for dropdown
        form.service_order_id.choices = [(0, 'Nenhuma OS relacionada')] + [
            (so.id, f'OS #{so.id} - {so.client.name}')
            for so in ServiceOrder.query.order_by(ServiceOrder.id.desc()).limit(100).all()
        ]
        
        if form.validate_on_submit():
            entry = FinancialEntry(
                service_order_id=form.service_order_id.data if form.service_order_id.data != 0 else None,
                description=form.description.data,
                amount=form.amount.data,
                type=FinancialEntryType[form.type.data],
                date=datetime.strptime(form.date.data, '%Y-%m-%d'),
                created_by=current_user.id
            )
            
            db.session.add(entry)
            db.session.commit()
            
            log_action(
                'Registro Financeiro',
                'financial',
                entry.id,
                f"Registro financeiro de {format_currency(entry.amount)} ({entry.type.value})"
            )
            
            flash('Registro financeiro adicionado com sucesso!', 'success')
            return redirect(url_for('financial'))
            
        # Set today's date as default
        if request.method == 'GET':
            form.date.data = datetime.utcnow().strftime('%Y-%m-%d')
            
        return render_template('financial/create.html', form=form)

    @app.route('/financeiro/exportar')
    @manager_required
    def export_financial():
        month = request.args.get('month', datetime.utcnow().month, type=int)
        year = request.args.get('year', datetime.utcnow().year, type=int)
        
        # Get entries for the selected month
        entries = FinancialEntry.query.filter(
            func.extract('month', FinancialEntry.date) == month,
            func.extract('year', FinancialEntry.date) == year
        ).order_by(FinancialEntry.date).all()
        
        # Generate CSV content
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Data', 'Descrição', 'Tipo', 'Valor', 'OS Relacionada'])
        
        for entry in entries:
            os_info = f'OS #{entry.service_order_id}' if entry.service_order_id else 'N/A'
            writer.writerow([
                entry.date.strftime('%d/%m/%Y'),
                entry.description,
                entry.type.value,
                f'{entry.amount:.2f}'.replace('.', ','),
                os_info
            ])
            
        # Create filename with month and year
        month_name = {
            1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
            5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
            9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
        }[month]
        
        filename = f'financeiro_{month_name}_{year}.csv'
        
        log_action(
            'Exportação Financeira',
            'financial',
            None,
            f"Exportação dos dados financeiros de {month_name}/{year}"
        )
        
        # Return CSV file
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv; charset=utf-8',
            'Content-Disposition': f'attachment; filename="{filename}"'
        }

    # Log routes
    @app.route('/logs')
    @admin_required
    def logs():
        page = request.args.get('page', 1, type=int)
        user_id = request.args.get('user_id', type=int)
        entity_type = request.args.get('entity_type', '')
        
        query = ActionLog.query
        
        if user_id:
            query = query.filter_by(user_id=user_id)
            
        if entity_type:
            query = query.filter_by(entity_type=entity_type)
            
        logs = query.order_by(ActionLog.timestamp.desc()).paginate(
            page=page, 
            per_page=50,
            error_out=False
        )
        
        users = User.query.order_by(User.name).all()
        
        return render_template(
            'logs/index.html',
            logs=logs,
            users=users,
            user_id=user_id,
            entity_type=entity_type
        )

    # Profile routes
    @app.route('/perfil', methods=['GET', 'POST'])
    @login_required
    def profile():
        form = ProfileForm(obj=current_user)
        
        if form.validate_on_submit():
            # Verify current password if changing password or email
            if (form.new_password.data or 
                form.email.data != current_user.email) and not current_user.check_password(form.current_password.data):
                flash('Senha atual incorreta.', 'danger')
                return render_template('profile/index.html', form=form)
                
            # Update name
            current_user.name = form.name.data
            
            # Update email if changed and provided current password
            if form.email.data != current_user.email:
                # Check if email is already in use
                if User.query.filter_by(email=form.email.data).first():
                    flash('Este email já está em uso por outro usuário.', 'danger')
                    return render_template('profile/index.html', form=form)
                    
                current_user.email = form.email.data
                
            # Handle profile image upload
            if form.profile_image.data and hasattr(form.profile_image.data, 'filename'):
                # Save the image
                import os
                from werkzeug.utils import secure_filename
                
                # Create the profiles directory if it doesn't exist
                os.makedirs('static/images/profiles', exist_ok=True)
                
                # Get the file extension
                filename = secure_filename(form.profile_image.data.filename)
                _, file_extension = os.path.splitext(filename)
                
                # Verificar extensão de arquivo
                if file_extension.lower() not in ['.jpg', '.jpeg', '.png', '.gif']:
                    flash('Formato de arquivo não permitido. Apenas JPG, JPEG, PNG e GIF são aceitos.', 'danger')
                    return render_template('profile/index.html', form=form)
                
                # Verificar tamanho do arquivo (max 2MB)
                form.profile_image.data.seek(0, os.SEEK_END)
                file_size = form.profile_image.data.tell()
                form.profile_image.data.seek(0)  # Retornar para o início do arquivo
                
                if file_size > 2 * 1024 * 1024:  # 2MB em bytes
                    flash('Tamanho do arquivo maior que 2MB. Por favor, escolha uma imagem menor.', 'danger')
                    return render_template('profile/index.html', form=form)
                
                # Remover imagem anterior se existir e não for a padrão
                if current_user.profile_image and current_user.profile_image != 'default_profile.svg':
                    old_file_path = os.path.join('static/images/profiles', current_user.profile_image)
                    if os.path.exists(old_file_path):
                        try:
                            os.remove(old_file_path)
                        except:
                            pass  # Se não conseguir remover, apenas continue
                
                # Create a unique filename based on user ID and timestamp para evitar cache do navegador
                timestamp = int(datetime.now().timestamp())
                profile_image_filename = f"user_{current_user.id}_{timestamp}{file_extension}"
                
                # Save the file
                file_path = os.path.join('static/images/profiles', profile_image_filename)
                form.profile_image.data.save(file_path)
                
                # Update the user's profile_image field
                current_user.profile_image = profile_image_filename
                
                # Log da alteração da imagem
                log_action(
                    'Atualização de Foto de Perfil',
                    'user',
                    current_user.id,
                    'Foto de perfil atualizada'
                )
            
            # Update password if provided
            if form.new_password.data:
                current_user.set_password(form.new_password.data)
                
            db.session.commit()
            
            log_action(
                'Atualização de Perfil',
                'user',
                current_user.id,
                'Perfil atualizado'
            )
            
            flash('Perfil atualizado com sucesso!', 'success')
            return redirect(url_for('profile'))
            
        return render_template('profile/index.html', form=form)

    # Invoice/NF-e routes
    @app.route('/notas-fiscais')
    @login_required
    def invoices():
        page = request.args.get('page', 1, type=int)
        per_page = 20  # Pode ser ajustado nas configurações do sistema posteriormente
        
        # Obtém ordens de serviço fechadas (com nota fiscal)
        query = ServiceOrder.query.filter(
            ServiceOrder.status == ServiceOrderStatus.fechada,
            ServiceOrder.invoice_number.isnot(None)
        ).order_by(ServiceOrder.invoice_date.desc())
        
        # Filtros
        cliente = request.args.get('cliente')
        numero_nf = request.args.get('numero_nf')
        data_inicio = request.args.get('data_inicio')
        data_fim = request.args.get('data_fim')
        
        if cliente:
            query = query.join(Client).filter(Client.name.ilike(f'%{cliente}%'))
        
        if numero_nf:
            query = query.filter(ServiceOrder.invoice_number.ilike(f'%{numero_nf}%'))
        
        if data_inicio:
            try:
                data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(ServiceOrder.invoice_date >= data_inicio)
            except ValueError:
                flash('Data inicial inválida.', 'warning')
        
        if data_fim:
            try:
                data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
                data_fim = datetime.combine(data_fim, datetime.max.time())  # Fim do dia
                query = query.filter(ServiceOrder.invoice_date <= data_fim)
            except ValueError:
                flash('Data final inválida.', 'warning')
        
        # Paginação
        invoices = query.paginate(page=page, per_page=per_page)
        
        return render_template('invoices/index.html', invoices=invoices)
    
    @app.route('/notas-fiscais/exportar')
    @login_required
    def export_invoices():
        import zipfile
        import io
        from weasyprint import HTML
        from flask import make_response
        import tempfile
        import os
        from decimal import Decimal
        
        try:
            # Obtém os mesmos filtros da listagem
            cliente = request.args.get('cliente')
            numero_nf = request.args.get('numero_nf')
            data_inicio = request.args.get('data_inicio')
            data_fim = request.args.get('data_fim')
            
            # Constrói a query com os mesmos filtros da página de listagem
            query = ServiceOrder.query.filter(
                ServiceOrder.status == ServiceOrderStatus.fechada,
                ServiceOrder.invoice_number.isnot(None)
            ).order_by(ServiceOrder.invoice_date.desc())
            
            if cliente:
                query = query.join(Client).filter(Client.name.ilike(f'%{cliente}%'))
            
            if numero_nf:
                query = query.filter(ServiceOrder.invoice_number.ilike(f'%{numero_nf}%'))
            
            if data_inicio:
                try:
                    data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
                    query = query.filter(ServiceOrder.invoice_date >= data_inicio)
                except ValueError:
                    flash('Data inicial inválida.', 'warning')
                    return redirect(url_for('invoices'))
            
            if data_fim:
                try:
                    data_fim = datetime.strptime(data_fim, '%Y-%m-%d')
                    data_fim = datetime.combine(data_fim, datetime.max.time())
                    query = query.filter(ServiceOrder.invoice_date <= data_fim)
                except ValueError:
                    flash('Data final inválida.', 'warning')
                    return redirect(url_for('invoices'))
            
            # Limita a quantidade para evitar arquivos muito grandes
            invoices = query.limit(50).all()
            
            if not invoices:
                flash('Nenhuma nota fiscal encontrada para exportação.', 'warning')
                return redirect(url_for('invoices'))
            
            # Cria um arquivo ZIP em memória
            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w') as zf:
                # Adiciona cada nota fiscal ao ZIP
                for so in invoices:
                    # Gera HTML da nota fiscal
                    html_content = render_template('invoices/view.html', 
                                                  service_order=so, 
                                                  export_mode=True,
                                                  Decimal=Decimal)  # Passando o tipo Decimal para o template
                    
                    # Cria arquivo PDF temporário
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp:
                        # Configurar tamanho A4 e outras opções para impressão
                        pdf_options = {
                            'page-size': 'A4',
                            'margin-top': '0.5cm',
                            'margin-right': '0.5cm',
                            'margin-bottom': '0.5cm',
                            'margin-left': '0.5cm',
                            'encoding': 'UTF-8',
                            'print-media-type': '',
                            'no-outline': None
                        }
                        
                        # Gera PDF do HTML com tamanho A4
                        HTML(string=html_content).write_pdf(temp.name, presentational_hints=True, stylesheets=[], **pdf_options)
                    
                    # Lê o arquivo PDF e adiciona ao ZIP
                    with open(temp.name, 'rb') as pdf_file:
                        pdf_data = pdf_file.read()
                        # Adiciona ao ZIP com um nome adequado
                        zf.writestr(f'NF_{so.invoice_number}.pdf', pdf_data)
                    
                    # Remove o arquivo temporário
                    os.unlink(temp.name)
            
            # Prepara o arquivo ZIP para download
            memory_file.seek(0)
            
            data_str = datetime.now().strftime('%Y%m%d')
            response = make_response(memory_file.getvalue())
            response.headers['Content-Type'] = 'application/zip'
            response.headers['Content-Disposition'] = f'attachment; filename=notas_fiscais_{data_str}.zip'
            
            # Registra a ação
            log_action(
                'Exportação de Notas Fiscais',
                None,
                None,
                f'Exportação de {len(invoices)} notas fiscais em PDF'
            )
            
            return response
        
        except Exception as e:
            # Log do erro
            app.logger.error(f"Erro ao exportar notas fiscais em massa: {str(e)}")
            flash(f'Erro ao exportar as notas fiscais: {str(e)}', 'danger')
            return redirect(url_for('invoices'))
    
    @app.route('/os/<int:id>/nfe')
    @login_required
    def view_invoice(id):
        from decimal import Decimal
        from datetime import datetime
        
        service_order = ServiceOrder.query.get_or_404(id)
        
        # Check if order is closed
        if service_order.status != ServiceOrderStatus.fechada:
            flash('Esta OS ainda não foi fechada.', 'warning')
            return redirect(url_for('view_service_order', id=id))
            
        # Verificar se a ordem de serviço possui cliente 
        if not service_order.client or not service_order.client_id:
            flash('Esta Ordem de Serviço não possui cliente associado e não pode gerar nota fiscal.', 'danger')
            return redirect(url_for('view_service_order', id=id))
        
        # Verificar e corrigir campos de data necessários
        if not service_order.invoice_date:
            service_order.invoice_date = datetime.utcnow()
            
        if not service_order.closed_at:
            service_order.closed_at = datetime.utcnow()
            
        # Verificar outros campos obrigatórios
        if not service_order.invoice_number:
            from utils import get_next_invoice_number
            service_order.invoice_number = get_next_invoice_number()
            
        # Salvar as alterações
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar informações da nota fiscal: {str(e)}', 'danger')
            return redirect(url_for('view_service_order', id=id))
        
        # Passamos o tipo Decimal para o template para facilitar operações matemáticas
        try:
            app.logger.debug(f"Renderizando template para OS #{id}. Service Order: {service_order}")
            if service_order.equipment:
                app.logger.debug(f"Equipamentos encontrados: {len(service_order.equipment)}")
            else:
                app.logger.debug("Nenhum equipamento associado.")
                
            return render_template('invoices/clean_invoice.html', 
                                service_order=service_order,
                                Decimal=Decimal)
        except Exception as e:
            flash(f'Erro ao gerar nota fiscal: {str(e)}', 'danger')
            app.logger.error(f"Erro ao gerar nota fiscal: {str(e)}")
            return redirect(url_for('view_service_order', id=id))
    
    @app.route('/os/<int:id>/nfe/exportar')
    @login_required
    def export_invoice(id):
        from weasyprint import HTML
        from flask import make_response
        import tempfile
        import os
        from decimal import Decimal
        from datetime import datetime
        
        service_order = ServiceOrder.query.get_or_404(id)
        
        # Check if order is closed
        if service_order.status != ServiceOrderStatus.fechada:
            flash('Esta OS ainda não foi fechada.', 'warning')
            return redirect(url_for('view_service_order', id=id))
            
        # Verificar e corrigir campos de data necessários
        if not service_order.invoice_date:
            service_order.invoice_date = datetime.utcnow()
            
        if not service_order.closed_at:
            service_order.closed_at = datetime.utcnow()
            
        # Verificar outros campos obrigatórios
        if not service_order.invoice_number:
            from utils import get_next_invoice_number
            service_order.invoice_number = get_next_invoice_number()
            
        # Verificar se a ordem de serviço possui cliente 
        if not service_order.client or not service_order.client_id:
            flash('Esta Ordem de Serviço não possui cliente associado e não pode gerar nota fiscal.', 'danger')
            return redirect(url_for('view_service_order', id=id))
            
        # Salvar as alterações
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar informações da nota fiscal: {str(e)}', 'danger')
            return redirect(url_for('view_service_order', id=id))
        
        # Render the clean invoice template to HTML
        try:
            html_content = render_template('invoices/clean_invoice.html', 
                                        service_order=service_order,
                                        Decimal=Decimal)  # Passando o tipo Decimal para o template
        except Exception as e:
            flash(f'Erro ao gerar nota fiscal: {str(e)}', 'danger')
            return redirect(url_for('view_service_order', id=id))
        
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp:
                # Configurar tamanho A4 e outras opções para impressão
                pdf_options = {
                    'page-size': 'A4',
                    'margin-top': '0.5cm',
                    'margin-right': '0.5cm',
                    'margin-bottom': '0.5cm',
                    'margin-left': '0.5cm',
                    'encoding': 'UTF-8',
                    'print-media-type': '',
                    'no-outline': None
                }
                
                # Generate PDF from HTML content with A4 size
                HTML(string=html_content).write_pdf(temp.name, presentational_hints=True, stylesheets=[], **pdf_options)
            
            # Create a response with the PDF file
            with open(temp.name, 'rb') as pdf_file:
                response = make_response(pdf_file.read())
                response.headers['Content-Type'] = 'application/pdf'
                response.headers['Content-Disposition'] = f'attachment; filename=nota_fiscal_{service_order.invoice_number}.pdf'
            
            # Clean up temporary file
            os.unlink(temp.name)
            
            # Log the successful export
            log_action(
                'Exportação de Nota Fiscal',
                'service_order',
                service_order.id,
                f'Nota fiscal {service_order.invoice_number} exportada com sucesso'
            )
            
            return response
            
        except Exception as e:
            # Log the error
            app.logger.error(f"Erro ao exportar nota fiscal: {str(e)}")
            flash(f'Erro ao exportar a nota fiscal: {str(e)}', 'danger')
            return redirect(url_for('view_invoice', id=id))
        
    # =====================================================================
    # Rotas para Fornecedores
    # =====================================================================
    @app.route('/fornecedores')
    @login_required
    def suppliers():
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        
        query = Supplier.query
        
        # Filtrar por pesquisa
        if search:
            query = query.filter(
                or_(
                    Supplier.name.ilike(f'%{search}%'),
                    Supplier.document.ilike(f'%{search}%'),
                    Supplier.contact_name.ilike(f'%{search}%'),
                    Supplier.email.ilike(f'%{search}%')
                )
            )
        
        # Ordenar fornecedores
        query = query.order_by(Supplier.name)
        
        # Paginação
        from utils import get_system_setting
        pagination = query.paginate(
            page=page,
            per_page=int(get_system_setting('items_per_page', '20')),
            error_out=False
        )
        
        suppliers = pagination.items
        
        return render_template(
            'suppliers/index.html',
            suppliers=suppliers,
            pagination=pagination,
            search=search
        )
    
    @app.route('/fornecedores/novo', methods=['GET', 'POST'])
    @login_required
    def new_supplier():
        form = SupplierForm()
        
        if form.validate_on_submit():
            supplier = Supplier(
                name=form.name.data,
                document=form.document.data,
                contact_name=form.contact_name.data,
                email=form.email.data,
                phone=form.phone.data,
                address=form.address.data,
                website=form.website.data,
                notes=form.notes.data
            )
            
            db.session.add(supplier)
            db.session.commit()
            
            log_action(
                'Cadastro de Fornecedor',
                'supplier',
                supplier.id,
                f'Fornecedor {supplier.name} cadastrado'
            )
            
            flash('Fornecedor cadastrado com sucesso!', 'success')
            return redirect(url_for('view_supplier', id=supplier.id))
        
        return render_template('suppliers/create.html', form=form)
    
    @app.route('/fornecedores/<int:id>')
    @login_required
    def view_supplier(id):
        supplier = Supplier.query.get_or_404(id)
        
        # Buscar peças do fornecedor
        parts = Part.query.filter_by(supplier_id=supplier.id).all()
        
        return render_template(
            'suppliers/view.html',
            supplier=supplier,
            parts=parts
        )
    
    @app.route('/fornecedores/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    def edit_supplier(id):
        supplier = Supplier.query.get_or_404(id)
        form = SupplierForm()
        
        if request.method == 'GET':
            form.id.data = supplier.id
            form.name.data = supplier.name
            form.document.data = supplier.document
            form.contact_name.data = supplier.contact_name
            form.email.data = supplier.email
            form.phone.data = supplier.phone
            form.address.data = supplier.address
            form.website.data = supplier.website
            form.notes.data = supplier.notes
        
        if form.validate_on_submit():
            supplier.name = form.name.data
            supplier.document = form.document.data
            supplier.contact_name = form.contact_name.data
            supplier.email = form.email.data
            supplier.phone = form.phone.data
            supplier.address = form.address.data
            supplier.website = form.website.data
            supplier.notes = form.notes.data
            
            db.session.commit()
            
            log_action(
                'Edição de Fornecedor',
                'supplier',
                supplier.id,
                f'Fornecedor {supplier.name} atualizado'
            )
            
            flash('Fornecedor atualizado com sucesso!', 'success')
            return redirect(url_for('view_supplier', id=supplier.id))
        
        return render_template('suppliers/edit.html', form=form, supplier=supplier)
    
    @app.route('/fornecedores/<int:id>/excluir', methods=['POST'])
    @login_required
    @admin_required
    def delete_supplier(id):
        supplier = Supplier.query.get_or_404(id)
        
        # Verificar se o fornecedor tem peças cadastradas
        if supplier.parts:
            flash('Não é possível excluir um fornecedor com peças cadastradas!', 'danger')
            return redirect(url_for('view_supplier', id=supplier.id))
        
        name = supplier.name
        db.session.delete(supplier)
        db.session.commit()
        
        log_action(
            'Exclusão de Fornecedor',
            'supplier',
            id,
            f'Fornecedor {name} excluído'
        )
        
        flash('Fornecedor excluído com sucesso!', 'success')
        return redirect(url_for('suppliers'))
    
    # =====================================================================
    # Rotas para Peças e Vendas
    # =====================================================================
    @app.route('/pecas')
    @login_required
    def parts():
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        low_stock = request.args.get('low_stock', False, type=bool)
        
        query = Part.query
        
        # Filtrar por pesquisa
        if search:
            query = query.filter(
                or_(
                    Part.name.ilike(f'%{search}%'),
                    Part.part_number.ilike(f'%{search}%'),
                    Part.description.ilike(f'%{search}%')
                )
            )
        
        # Filtrar por categoria
        if category:
            query = query.filter(Part.category == category)
        
        # Filtrar por estoque baixo
        if low_stock:
            query = query.filter(Part.stock_quantity <= Part.minimum_stock)
        
        # Ordenar peças
        query = query.order_by(Part.name)
        
        # Paginação
        from utils import get_system_setting
        pagination = query.paginate(
            page=page,
            per_page=int(get_system_setting('items_per_page', '20')),
            error_out=False
        )
        
        parts = pagination.items
        
        # Obter categorias para filtro
        categories = db.session.query(Part.category.distinct()).filter(Part.category.isnot(None)).order_by(Part.category).all()
        categories = [c[0] for c in categories if c[0]]
        
        return render_template(
            'parts/index.html',
            parts=parts,
            pagination=pagination,
            search=search,
            category=category,
            categories=categories,
            low_stock=low_stock
        )
    
    @app.route('/pecas/nova', methods=['GET', 'POST'])
    @login_required
    def new_part():
        form = PartForm()
        
        if form.validate_on_submit():
            try:
                # Processar upload de imagem, se houver
                image_filename = None
                if form.image.data:
                    try:
                        image = form.image.data
                        # Gerar nome de arquivo único
                        from werkzeug.utils import secure_filename
                        filename = secure_filename(f"{form.name.data.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{image.filename.split('.')[-1]}")
                        image_path = os.path.join('static', 'uploads', 'parts', filename)
                        os.makedirs(os.path.join('static', 'uploads', 'parts'), exist_ok=True)
                        image.save(image_path)
                        image_filename = filename
                    except Exception as e:
                        # Se houver erro no upload da imagem, registrar, mas continuar sem a imagem
                        app.logger.error(f"Erro ao salvar imagem da peça: {str(e)}")
                        flash("Não foi possível salvar a imagem da peça, mas o cadastro será feito mesmo assim.", "warning")
                
                part = Part(
                    name=form.name.data,
                    description=form.description.data,
                    part_number=form.part_number.data,
                    supplier_id=form.supplier_id.data if form.supplier_id.data else None,
                    category=form.category.data,
                    subcategory=form.subcategory.data,
                    cost_price=form.cost_price.data,
                    selling_price=form.selling_price.data,
                    stock_quantity=form.stock_quantity.data,
                    minimum_stock=form.minimum_stock.data,
                    location=form.location.data,
                    image=image_filename
                )
                
                db.session.add(part)
                db.session.commit()
                
                try:
                    log_action(
                        'Cadastro de Peça',
                        'part',
                        part.id,
                        f'Peça {part.name} cadastrada'
                    )
                except Exception:
                    # Se falhar ao registrar log, não interromper o fluxo principal
                    app.logger.error(f"Erro ao registrar log de criação da peça {part.id}")
                    
                flash('Peça cadastrada com sucesso!', 'success')
                return redirect(url_for('parts'))
                
            except IntegrityError:
                db.session.rollback()
                flash('Erro de integridade ao cadastrar peça. Verifique se já existe uma peça com o mesmo número.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao cadastrar peça: {str(e)}', 'danger')
                app.logger.error(f"Erro ao cadastrar peça: {str(e)}")
                
        # Se chegou aqui é porque o formulário não foi validado ou ocorreu erro
        return render_template('parts/create.html', form=form)
    
    @app.route('/pecas/<int:id>')
    @login_required
    def view_part(id):
        part = Part.query.get_or_404(id)
        
        # Buscar histórico de vendas
        sales = PartSale.query.filter_by(part_id=part.id).order_by(PartSale.sale_date.desc()).all()
        
        return render_template(
            'parts/view.html',
            part=part,
            sales=sales
        )
    
    @app.route('/pecas/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    def edit_part(id):
        part = Part.query.get_or_404(id)
        form = PartForm()
        
        if request.method == 'GET':
            form.id.data = part.id
            form.name.data = part.name
            form.description.data = part.description
            form.part_number.data = part.part_number
            form.supplier_id.data = part.supplier_id
            form.category.data = part.category
            form.subcategory.data = part.subcategory
            form.cost_price.data = part.cost_price
            form.selling_price.data = part.selling_price
            form.stock_quantity.data = part.stock_quantity
            form.minimum_stock.data = part.minimum_stock
            form.location.data = part.location
        
        if form.validate_on_submit():
            # Processar upload de imagem, se houver
            if form.image.data:
                image = form.image.data
                # Gerar nome de arquivo único
                from werkzeug.utils import secure_filename
                filename = secure_filename(f"{form.name.data.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{image.filename.split('.')[-1]}")
                image_path = os.path.join('static', 'uploads', 'parts', filename)
                os.makedirs(os.path.join('static', 'uploads', 'parts'), exist_ok=True)
                image.save(image_path)
                part.image = filename
            
            part.name = form.name.data
            part.description = form.description.data
            part.part_number = form.part_number.data
            part.supplier_id = form.supplier_id.data if form.supplier_id.data else None
            part.category = form.category.data
            part.subcategory = form.subcategory.data
            part.cost_price = form.cost_price.data
            part.selling_price = form.selling_price.data
            part.stock_quantity = form.stock_quantity.data
            part.minimum_stock = form.minimum_stock.data
            part.location = form.location.data
            
            db.session.commit()
            
            log_action(
                'Edição de Peça',
                'part',
                part.id,
                f'Peça {part.name} atualizada'
            )
            
            flash('Peça atualizada com sucesso!', 'success')
            return redirect(url_for('view_part', id=part.id))
        
        return render_template('parts/edit.html', form=form, part=part)
    
    @app.route('/pecas/<int:id>/excluir', methods=['POST'])
    @login_required
    @admin_required
    def delete_part(id):
        part = Part.query.get_or_404(id)
        
        # Verificar se a peça tem vendas registradas
        if part.sales:
            flash('Não é possível excluir uma peça com vendas registradas!', 'danger')
            return redirect(url_for('view_part', id=part.id))
        
        name = part.name
        
        # Remover a imagem, se existir
        if part.image:
            image_path = os.path.join('static', 'uploads', 'parts', part.image)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(part)
        db.session.commit()
        
        log_action(
            'Exclusão de Peça',
            'part',
            id,
            f'Peça {name} excluída'
        )
        
        flash('Peça excluída com sucesso!', 'success')
        return redirect(url_for('parts'))
    
    @app.route('/vendas-pecas')
    @login_required
    def part_sales():
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        client_id = request.args.get('client_id', None, type=int)
        service_order_id = request.args.get('service_order_id', None, type=int)
        
        query = PartSale.query
        
        # Filtrar por pesquisa
        if search:
            query = query.join(Part).filter(
                or_(
                    Part.name.ilike(f'%{search}%'),
                    Part.part_number.ilike(f'%{search}%'),
                    PartSale.invoice_number.ilike(f'%{search}%')
                )
            )
        
        # Filtrar por cliente
        if client_id:
            query = query.filter(PartSale.client_id == client_id)
        
        # Filtrar por ordem de serviço
        if service_order_id:
            query = query.filter(PartSale.service_order_id == service_order_id)
        
        # Ordenar vendas
        query = query.order_by(PartSale.sale_date.desc())
        
        # Paginação
        from utils import get_system_setting
        pagination = query.paginate(
            page=page,
            per_page=int(get_system_setting('items_per_page', '20')),
            error_out=False
        )
        
        sales = pagination.items
        
        # Obter clientes para filtro
        clients = Client.query.order_by(Client.name).all()
        
        # Obter ordens de serviço para filtro
        service_orders = ServiceOrder.query.order_by(ServiceOrder.id.desc()).all()
        
        return render_template(
            'part_sales/index.html',
            sales=sales,
            pagination=pagination,
            search=search,
            client_id=client_id,
            service_order_id=service_order_id,
            clients=clients,
            service_orders=service_orders
        )
    
    @app.route('/vendas-pecas/nova', methods=['GET', 'POST'])
    @login_required
    def new_part_sale():
        form = PartSaleForm()
        
        # Pré-preencher dados se vier de uma ordem de serviço
        service_order_id = request.args.get('service_order_id', None, type=int)
        if service_order_id:
            form.service_order_id.data = service_order_id
            service_order = ServiceOrder.query.get(service_order_id)
            if service_order:
                form.client_id.data = service_order.client_id
        
        # Pré-preencher dados se vier de uma peça específica
        part_id = request.args.get('part_id', None, type=int)
        if part_id:
            form.part_id.data = part_id
            part = Part.query.get(part_id)
            if part:
                form.unit_price.data = part.selling_price
                form.total_price.data = part.selling_price
        
        if form.validate_on_submit():
            # Obter a peça e verificar estoque
            part = Part.query.get(form.part_id.data)
            if not part:
                flash('Peça não encontrada!', 'danger')
                return redirect(url_for('new_part_sale'))
            
            if part.stock_quantity < form.quantity.data:
                flash(f'Estoque insuficiente! Disponível: {part.stock_quantity}', 'danger')
                return render_template('part_sales/create.html', form=form)
            
            # Criar a venda
            sale = PartSale(
                part_id=form.part_id.data,
                client_id=form.client_id.data if form.client_id.data else None,
                service_order_id=form.service_order_id.data if form.service_order_id.data else None,
                quantity=form.quantity.data,
                unit_price=form.unit_price.data,
                total_price=form.total_price.data,
                invoice_number=form.invoice_number.data,
                notes=form.notes.data,
                created_by=current_user.id
            )
            
            # Atualizar o estoque da peça
            part.stock_quantity -= form.quantity.data
            
            # Adicionar entrada financeira sempre, independentemente de estar associada a uma OS
            description = f"Venda de peça: {part.name} (x{sale.quantity})"
            if sale.client_id:
                client = Client.query.get(sale.client_id)
                if client:
                    description += f" - Cliente: {client.name}"
            
            if sale.invoice_number:
                description += f" - NF-e: {sale.invoice_number}"
                
            financial_entry = FinancialEntry(
                service_order_id=sale.service_order_id if sale.service_order_id else None,
                description=description,
                amount=sale.total_price,
                type=FinancialEntryType.entrada,
                date=datetime.now(),
                created_by=current_user.id
            )
            db.session.add(financial_entry)
            
            db.session.add(sale)
            db.session.commit()
            
            log_action(
                'Venda de Peça',
                'part_sale',
                sale.id,
                f'Venda de {sale.quantity}x {part.name} realizada'
            )
            
            flash('Venda registrada com sucesso!', 'success')
            
            # Redirecionar para a ordem de serviço, se associada
            if sale.service_order_id:
                return redirect(url_for('view_service_order', id=sale.service_order_id))
            return redirect(url_for('part_sales'))
        
        return render_template('part_sales/create.html', form=form)
    
    @app.route('/vendas-pecas/<int:id>')
    @login_required
    def view_part_sale(id):
        sale = PartSale.query.get_or_404(id)
        form = FlaskForm()  # Formulário vazio apenas para o token CSRF
        return render_template('part_sales/view.html', sale=sale, form=form)
    
    @app.route('/vendas-pecas/<int:id>/cancelar', methods=['POST'])
    @login_required
    @admin_required
    def cancel_part_sale(id):
        form = FlaskForm()  # Formulário vazio apenas para o token CSRF
        if not form.validate_on_submit():
            flash('Erro de segurança: Token CSRF inválido. Tente novamente.', 'danger')
            return redirect(url_for('view_part_sale', id=id))
            
        sale = PartSale.query.get_or_404(id)
        
        # Restaurar estoque
        part = Part.query.get(sale.part_id)
        if part:
            part.stock_quantity += sale.quantity
        
        # Remover entrada financeira associada, sempre
        # Primeiro tenta buscar pela ordem de serviço, se tiver
        financial_entry = None
        if sale.service_order_id:
            financial_entry = FinancialEntry.query.filter_by(
                service_order_id=sale.service_order_id,
                amount=sale.total_price,
                type=FinancialEntryType.entrada
            ).first()
        
        # Se não encontrou, tenta buscar pela descrição contendo o nome da peça e quantidade
        if not financial_entry:
            description_pattern = f"Venda de peça: {part.name} (x{sale.quantity})"
            financial_entry = FinancialEntry.query.filter(
                FinancialEntry.description.like(f"%{description_pattern}%"),
                FinancialEntry.amount == sale.total_price,
                FinancialEntry.type == FinancialEntryType.entrada
            ).first()
        
        # Remove a entrada financeira, se encontrada
        if financial_entry:
            db.session.delete(financial_entry)
        
        # Registrar o cancelamento no log
        log_action(
            'Cancelamento de Venda',
            'part_sale',
            id,
            f'Venda de {sale.quantity}x {part.name} cancelada'
        )
        
        db.session.delete(sale)
        db.session.commit()
        
        flash('Venda cancelada com sucesso!', 'success')
        return redirect(url_for('part_sales'))
    
    # Rota de ajuste de estoque
    @app.route('/pecas/<int:id>/ajustar-estoque', methods=['GET', 'POST'])
    @login_required
    @manager_required
    def adjust_stock(id):
        part = Part.query.get_or_404(id)
        form = FlaskForm()  # Formulário vazio apenas para o token CSRF
        
        if request.method == 'POST' and form.validate_on_submit():
            quantity = request.form.get('quantity', type=int)
            reason = request.form.get('reason')
            
            if not quantity:
                flash('Quantidade inválida!', 'danger')
                return redirect(url_for('view_part', id=part.id))
            
            old_quantity = part.stock_quantity
            part.stock_quantity = quantity
            
            db.session.commit()
            
            log_action(
                'Ajuste de Estoque',
                'part',
                part.id,
                f'Estoque ajustado de {old_quantity} para {quantity} unidades. Motivo: {reason}'
            )
            
            flash('Estoque ajustado com sucesso!', 'success')
            return redirect(url_for('view_part', id=part.id))
        
        return render_template('parts/adjust_stock.html', part=part, form=form)

    # Rotas de Pedidos a Fornecedores
    @app.route('/pedidos-fornecedor')
    @login_required
    def supplier_orders():
        page = request.args.get('page', 1, type=int)
        per_page = 20  # Itens por página
        
        query = SupplierOrder.query
        
        # Filtros
        supplier_id = request.args.get('supplier_id', type=int)
        status = request.args.get('status')
        
        if supplier_id:
            query = query.filter(SupplierOrder.supplier_id == supplier_id)
        
        if status:
            query = query.filter(SupplierOrder.status == status)
        
        orders = query.order_by(SupplierOrder.created_at.desc()).paginate(page=page, per_page=per_page)
        
        # Fornecedores para o filtro
        suppliers = Supplier.query.order_by(Supplier.name).all()
        
        return render_template(
            'supplier_orders/index.html', 
            orders=orders,
            suppliers=suppliers,
            order_statuses=OrderStatus,
            current_supplier=supplier_id,
            current_status=status
        )
    
    @app.route('/pedidos-fornecedor/novo', methods=['GET', 'POST'])
    @login_required
    def new_supplier_order():
        form = SupplierOrderForm()
        
        # Buscar peças para o dropdown no modal de adicionar item
        parts = Part.query.order_by(Part.name).all()
        
        if form.validate_on_submit():
            try:
                # Formatar as datas
                expected_delivery_date = None
                if form.expected_delivery_date.data:
                    try:
                        expected_delivery_date = datetime.strptime(form.expected_delivery_date.data, '%d/%m/%Y').date()
                    except ValueError:
                        flash('Formato de data inválido. Use DD/MM/AAAA', 'danger')
                        return render_template('supplier_orders/create.html', form=form, parts=parts)
                
                delivery_date = None
                if form.delivery_date.data:
                    try:
                        delivery_date = datetime.strptime(form.delivery_date.data, '%d/%m/%Y').date()
                    except ValueError:
                        flash('Formato de data inválido. Use DD/MM/AAAA', 'danger')
                        return render_template('supplier_orders/create.html', form=form, parts=parts)
                
                # Criar o pedido
                order = SupplierOrder(
                    supplier_id=form.supplier_id.data,
                    order_number=form.order_number.data,
                    total_value=0,  # Inicialmente zero, será calculado ao adicionar itens
                    status=form.status.data,
                    expected_delivery_date=expected_delivery_date,
                    delivery_date=delivery_date,
                    notes=form.notes.data,
                    created_by=current_user.id
                )
                
                db.session.add(order)
                db.session.commit()
                
                # Processar itens do pedido (enviados como JSON)
                items_json = request.form.get('items_json', '[]')
                try:
                    items_data = json.loads(items_json)
                    for item_data in items_data:
                        # Criar item de pedido
                        item = OrderItem(
                            order_id=order.id,
                            part_id=item_data.get('part_id') if item_data.get('part_id') else None,
                            description=item_data.get('description', ''),
                            quantity=item_data.get('quantity', 1),
                            unit_price=item_data.get('unit_price', 0),
                            total_price=item_data.get('total_price', 0),
                            status=OrderStatus.pendente
                        )
                        db.session.add(item)
                    
                    db.session.commit()
                    
                    try:
                        # Registrar log apenas após confirmação do commit de todos os itens
                        log_action(
                            'Criação de Pedido',
                            'supplier_order',
                            order.id,
                            f'Pedido para {order.supplier.name} criado'
                        )
                    except Exception as log_error:
                        app.logger.error(f"Erro ao registrar log de pedido: {str(log_error)}")
                        
                    flash('Pedido criado com sucesso!', 'success')
                    return redirect(url_for('view_supplier_order', id=order.id))
                    
                except Exception as item_error:
                    # Erro ao processar itens do pedido, reverter a transação e mostrar mensagem de erro
                    db.session.rollback()
                    app.logger.error(f"Erro ao processar itens do pedido: {str(item_error)}")
                    flash(f'Erro ao processar itens do pedido: {str(item_error)}', 'danger')
                    return render_template('supplier_orders/create.html', form=form, parts=parts)
                
            except IntegrityError:
                db.session.rollback()
                flash('Erro de integridade ao criar pedido. Verifique se já existe um pedido com o mesmo número.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Erro ao criar pedido: {str(e)}', 'danger')
                app.logger.error(f"Erro ao criar pedido: {str(e)}")
        
        return render_template('supplier_orders/create.html', form=form, parts=parts)
    
    @app.route('/pedidos-fornecedor/<int:id>')
    @login_required
    def view_supplier_order(id):
        from utils import is_order_paid
        
        order = SupplierOrder.query.get_or_404(id)
        item_form = OrderItemForm()
        is_paid = is_order_paid(id)
        
        return render_template(
            'supplier_orders/view.html', 
            order=order,
            item_form=item_form,
            order_statuses=OrderStatus,
            is_paid=is_paid
        )
    
    @app.route('/pedidos-fornecedor/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    def edit_supplier_order(id):
        order = SupplierOrder.query.get_or_404(id)
        form = SupplierOrderForm(obj=order)
        
        # Formatar datas para exibição no formulário
        if order.expected_delivery_date:
            form.expected_delivery_date.data = order.expected_delivery_date.strftime('%d/%m/%Y')
        
        if order.delivery_date:
            form.delivery_date.data = order.delivery_date.strftime('%d/%m/%Y')
        
        if form.validate_on_submit():
            # Formatar as datas
            expected_delivery_date = None
            if form.expected_delivery_date.data:
                try:
                    expected_delivery_date = datetime.strptime(form.expected_delivery_date.data, '%d/%m/%Y').date()
                except ValueError:
                    flash('Formato de data inválido. Use DD/MM/AAAA', 'danger')
                    return render_template('supplier_orders/edit.html', form=form, order=order)
            
            delivery_date = None
            if form.delivery_date.data:
                try:
                    delivery_date = datetime.strptime(form.delivery_date.data, '%d/%m/%Y').date()
                except ValueError:
                    flash('Formato de data inválido. Use DD/MM/AAAA', 'danger')
                    return render_template('supplier_orders/edit.html', form=form, order=order)
            
            # Atualizar os campos do pedido
            order.supplier_id = form.supplier_id.data
            order.order_number = form.order_number.data
            
            # Calcular o valor total automaticamente com base nos itens
            total = db.session.query(func.sum(OrderItem.total_price)).filter(OrderItem.order_id == order.id).scalar() or 0
            order.total_value = total
            
            order.status = form.status.data
            order.expected_delivery_date = expected_delivery_date
            order.delivery_date = delivery_date
            order.notes = form.notes.data
            
            db.session.commit()
            
            log_action(
                'Edição de Pedido',
                'supplier_order',
                order.id,
                f'Pedido para {order.supplier.name} atualizado'
            )
            
            flash('Pedido atualizado com sucesso!', 'success')
            return redirect(url_for('view_supplier_order', id=order.id))
        
        # Formulário para adicionar novos itens
        item_form = OrderItemForm()
        return render_template('supplier_orders/edit.html', form=form, order=order, item_form=item_form)
    
    @app.route('/pedidos-fornecedor/<int:id>/excluir', methods=['POST'])
    @login_required
    def delete_supplier_order(id):
        order = SupplierOrder.query.get_or_404(id)
        supplier_name = order.supplier.name
        
        # Registrar a ação antes de excluir
        log_action(
            'Exclusão de Pedido',
            'supplier_order',
            order.id,
            f'Pedido {order.order_number or "#" + str(order.id)} para {supplier_name} excluído'
        )
        
        db.session.delete(order)
        db.session.commit()
        
        flash('Pedido excluído com sucesso!', 'success')
        return redirect(url_for('supplier_orders'))
    
    # Função para recalcular o valor total do pedido
    def recalculate_supplier_order_total(order_id):
        # Somar todos os itens
        total = db.session.query(func.sum(OrderItem.total_price)).filter(OrderItem.order_id == order_id).scalar() or 0
        order = SupplierOrder.query.get(order_id)
        if order:
            order.total_value = total
            db.session.commit()
    
    @app.route('/pedidos-fornecedor/item/<int:id>/adicionar', methods=['POST'])
    @login_required
    def add_order_item(id):
        order = SupplierOrder.query.get_or_404(id)
        form = OrderItemForm()
        
        if form.validate_on_submit():
            # Adicionar novo item ao pedido
            item = OrderItem(
                order_id=order.id,
                stock_item_id=form.stock_item_id.data if form.stock_item_id.data else None,
                description=form.description.data,
                quantity=form.quantity.data,
                unit_price=form.unit_price.data or 0,
                total_price=form.total_price.data or 0,
                status=form.status.data,
                notes=form.notes.data
            )
            
            db.session.add(item)
            db.session.commit()
            
            # Atualizar o valor total do pedido
            recalculate_supplier_order_total(order.id)
            
            flash('Item adicionado com sucesso!', 'success')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'Erro no campo {getattr(form, field).label.text}: {error}', 'danger')
        
        return redirect(url_for('view_supplier_order', id=order.id))
        
    @app.route('/pedidos-fornecedor/item/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    def edit_order_item(id):
        item = OrderItem.query.get_or_404(id)
        order_id = item.order_id
        form = OrderItemForm(obj=item)
        
        if request.method == 'GET':
            # Preencher o formulário com os valores atuais
            if item.stock_item_id:
                form.stock_item_id.data = item.stock_item_id
        
        if form.validate_on_submit():
            # Atualizar o item
            item.stock_item_id = form.stock_item_id.data if form.stock_item_id.data else None
            item.description = form.description.data
            item.quantity = form.quantity.data
            item.unit_price = form.unit_price.data or 0
            item.total_price = form.total_price.data or 0
            item.status = form.status.data
            item.notes = form.notes.data
            
            db.session.commit()
            
            # Recalcular o valor total do pedido
            recalculate_supplier_order_total(order_id)
            
            flash('Item atualizado com sucesso!', 'success')
            return redirect(url_for('view_supplier_order', id=order_id))
        
        elif request.method == 'POST':
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'Erro no campo {getattr(form, field).label.text}: {error}', 'danger')
        
        return render_template('supplier_orders/edit_item.html', form=form, item=item)
    
    @app.route('/pedidos-fornecedor/item/<int:id>/excluir', methods=['POST'])
    @login_required
    def delete_order_item(id):
        item = OrderItem.query.get_or_404(id)
        order_id = item.order_id
        
        db.session.delete(item)
        db.session.commit()
        
        # Recalcular o valor total do pedido
        recalculate_supplier_order_total(order_id)
        
        flash('Item excluído com sucesso!', 'success')
        return redirect(url_for('view_supplier_order', id=order_id))
    
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
        
        return render_template(
            'stock/index.html',
            items=items,
            item_types=StockItemType,
            item_statuses=StockItemStatus,
            suppliers=suppliers,
            active_filters={
                'type': item_type,
                'status': status,
                'search': search,
                'supplier_id': supplier_id
            }
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
            
            app.logger.info(f"Renderizando template com {vehicles.total} veículos encontrados")
            
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
                stats=stats
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
        
        # Data atual para o modal de abastecimento
        now_date = datetime.now().strftime('%Y-%m-%d')
        
        return render_template(
            'fleet/view.html',
            vehicle=vehicle,
            maintenance_history=maintenance_history,
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
    @role_required(['admin', 'gerente'])
    def delete_vehicle(id):
        """Excluir veículo - redirecionar para a versão correta"""
        # Redirecionar para a nova rota de exclusão de veículos
        return redirect(url_for('delete_fleet_vehicle', id=id))
        
    @app.route('/frota/<int:id>/manutencao/nova', methods=['GET', 'POST'])
    @login_required
    @manager_required
    def new_vehicle_maintenance(id):
        """Registrar nova manutenção para um veículo"""
        vehicle = Vehicle.query.get_or_404(id)
        form = VehicleMaintenanceForm()
        
        # Pré-selecionar o veículo
        form.vehicle_id.data = vehicle.id
        
        # Passar o veículo para o template
        today = datetime.now().strftime('%Y-%m-%d')
        
        if form.validate_on_submit():
            try:
                # Converter a data
                maintenance_date = datetime.strptime(form.date.data, '%Y-%m-%d').date()
                
                # Criar registro de manutenção
                maintenance = VehicleMaintenance(
                    vehicle_id=form.vehicle_id.data,
                    date=maintenance_date,
                    odometer=form.mileage.data,  # Usando a coluna real: odometer em vez de property: mileage
                    description=form.description.data,
                    cost=form.cost.data,
                    workshop=form.service_provider.data,  # Usando a coluna real: workshop em vez de property: service_provider
                    invoice_number=form.invoice_number.data,
                    created_by=current_user.id  # Definindo o criador diretamente
                )
                
                db.session.add(maintenance)
                
                # Atualizar dados do veículo
                # Não definir last_maintenance_date pois não temos esse campo no modelo
                
                # Atualizar hodômetro do veículo se o valor informado é maior que o atual
                if form.mileage.data and (vehicle.current_km is None or form.mileage.data > vehicle.current_km):
                    vehicle.current_km = form.mileage.data
                
                db.session.commit()
                
                # Criar entrada financeira se houver custo
                if form.cost.data:
                    financial_entry = FinancialEntry(
                        description=f"Manutenção do veículo placa {vehicle.plate} - {form.description.data[:50]}",
                        amount=form.cost.data,
                        type=FinancialEntryType.saida,
                        date=maintenance_date,
                        created_by=current_user.id,
                        entry_type='vehicle_maintenance',
                        reference_id=maintenance.id
                    )
                    
                    db.session.add(financial_entry)
                    db.session.commit()
                
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
                flash(f'Erro ao registrar manutenção: {str(e)}', 'danger')
                app.logger.error(f"Erro ao registrar manutenção para veículo {id}: {str(e)}")
        
        return render_template('fleet/new_maintenance.html', form=form, vehicle=vehicle, today=today)
        
    @app.route('/frota/veiculos/<int:id>/excluir', methods=['POST'])
    @login_required
    @role_required(['admin', 'gerente'])
    def delete_fleet_vehicle(id):
        """Rota para excluir um veículo da frota"""
        vehicle = Vehicle.query.get_or_404(id)
        
        try:
            # Registrar informações para log
            vehicle_info = f"{vehicle.plate} ({vehicle.brand} {vehicle.model})"
            
            # Recuperar registros relacionados para excluir manualmente se necessário
            maintenance_records = VehicleMaintenance.query.filter_by(vehicle_id=id).all()
            refueling_records = Refueling.query.filter_by(vehicle_id=id).all()
            travel_logs = VehicleTravelLog.query.filter_by(vehicle_id=id).all()
            
            # Excluir registros financeiros relacionados às manutenções
            for maintenance in maintenance_records:
                # Buscar entradas financeiras relacionadas à manutenção
                description = f"Manutenção - {vehicle.brand} {vehicle.model} ({vehicle.plate})"
                financial_entries = FinancialEntry.query.filter(
                    FinancialEntry.description.like(f"%{description}%")
                ).all()
                
                for entry in financial_entries:
                    db.session.delete(entry)
            
            # Excluir registros financeiros relacionados aos abastecimentos
            for refueling in refueling_records:
                # Buscar entradas financeiras relacionadas aos abastecimentos
                description = f"Abastecimento - {vehicle.brand} {vehicle.model} ({vehicle.plate})"
                financial_entries = FinancialEntry.query.filter(
                    FinancialEntry.description.like(f"%{description}%")
                ).all()
                
                for entry in financial_entries:
                    db.session.delete(entry)
            
            # Excluir o veículo (as relações com cascade devem excluir automaticamente os registros dependentes)
            db.session.delete(vehicle)
            db.session.commit()
            
            flash(f'Veículo {vehicle_info} excluído com sucesso!', 'success')
            log_action(
                'Exclusão de Veículo',
                'vehicle',
                id,
                f"Veículo {vehicle_info} excluído do sistema"
            )
            
            return redirect(url_for('fleet'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao excluir o veículo: {str(e)}', 'danger')
            app.logger.error(f"Erro ao excluir veículo {id}: {str(e)}")
            return redirect(url_for('view_vehicle', id=id))
    
    @app.route('/frota/veiculos/<int:id>/abastecimento', methods=['GET', 'POST'])
    @login_required
    @manager_required
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
                
                # Criar lançamento financeiro com mais detalhes
                financial_entry = FinancialEntry(
                    date=refueling_date,
                    amount=total_cost,
                    description=f"Abastecimento - {vehicle.brand} {vehicle.model} ({vehicle.plate}) - Combustível",
                    type=FinancialEntryType.saida,
                    # Removidos campos inválidos (payment_method e category)
                    created_by=current_user.id,
                    entry_type='vehicle_refueling',
                    reference_id=refueling.id
                )
                
                # Salvar no banco de dados
                db.session.add(refueling)
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
