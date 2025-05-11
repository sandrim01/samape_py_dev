import os
from datetime import datetime
from functools import wraps
from flask import render_template, redirect, url_for, flash, request, jsonify, session, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import func, desc, or_

from app import db
from models import (
    User, Client, Equipment, ServiceOrder, FinancialEntry, ActionLog,
    UserRole, ServiceOrderStatus, FinancialEntryType
)
from forms import (
    LoginForm, UserForm, ClientForm, EquipmentForm, ServiceOrderForm,
    CloseServiceOrderForm, FinancialEntryForm, ProfileForm
)
from utils import (
    role_required, admin_required, manager_required, log_action,
    check_login_attempts, record_login_attempt, format_document,
    format_currency, get_monthly_summary, get_service_order_stats
)

def register_routes(app):
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
        return {
            'format_document': format_document,
            'format_currency': format_currency,
            'UserRole': UserRole,
            'ServiceOrderStatus': ServiceOrderStatus,
            'FinancialEntryType': FinancialEntryType,
            'now': datetime.utcnow
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
                login_user(user, remember=form.remember_me.data)
                record_login_attempt(username, True)
                log_action('Login', 'user', user.id)
                
                next_page = request.args.get('next')
                if not next_page or not next_page.startswith('/'):
                    next_page = url_for('dashboard')
                
                return redirect(next_page)
            else:
                record_login_attempt(username, False)
                flash('Nome de usuário ou senha inválidos.', 'danger')
        
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        log_action('Logout', 'user', current_user.id)
        logout_user()
        flash('Você foi desconectado com sucesso.', 'success')
        return redirect(url_for('login'))

    # Dashboard
    @app.route('/dashboard')
    @login_required
    def dashboard():
        # Get service order statistics
        so_stats = get_service_order_stats()
        
        # Get financial summary
        financial_summary = get_monthly_summary()
        
        # Get recent service orders
        recent_orders = ServiceOrder.query.order_by(
            ServiceOrder.created_at.desc()
        ).limit(5).all()
        
        # Get recent activity logs
        recent_logs = ActionLog.query.order_by(
            ActionLog.timestamp.desc()
        ).limit(10).all()
        
        return render_template(
            'dashboard.html',
            so_stats=so_stats,
            financial_summary=financial_summary,
            recent_orders=recent_orders,
            recent_logs=recent_logs
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
            
            log_action(
                'Criação de OS',
                'service_order',
                service_order.id,
                f"OS criada para cliente {service_order.client.name}"
            )
            
            flash('Ordem de serviço criada com sucesso!', 'success')
            return redirect(url_for('service_orders'))
            
        return render_template(
            'service_orders/create.html',
            form=form
        )

    @app.route('/os/<int:id>')
    @login_required
    def view_service_order(id):
        service_order = ServiceOrder.query.get_or_404(id)
        return render_template('service_orders/view.html', service_order=service_order)

    @app.route('/os/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    def edit_service_order(id):
        service_order = ServiceOrder.query.get_or_404(id)
        
        # Check if order is already closed
        if service_order.status == ServiceOrderStatus.fechada:
            flash('Não é possível editar uma OS fechada.', 'warning')
            return redirect(url_for('view_service_order', id=id))
            
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
                
        if form.validate_on_submit():
            service_order.client_id = form.client_id.data
            service_order.responsible_id = form.responsible_id.data if form.responsible_id.data != 0 else None
            service_order.description = form.description.data
            service_order.estimated_value = form.estimated_value.data
            service_order.status = ServiceOrderStatus[form.status.data]
            
            # Update equipment relationships
            service_order.equipment = []
            if form.equipment_ids.data:
                equipment_ids = form.equipment_ids.data.split(',')
                for eq_id in equipment_ids:
                    equipment = Equipment.query.get(int(eq_id))
                    if equipment and equipment.client_id == service_order.client_id:
                        service_order.equipment.append(equipment)
            
            db.session.commit()
            
            log_action(
                'Edição de OS',
                'service_order',
                service_order.id,
                f"OS {id} atualizada"
            )
            
            flash('Ordem de serviço atualizada com sucesso!', 'success')
            return redirect(url_for('service_orders'))
            
        return render_template(
            'service_orders/edit.html',
            form=form,
            service_order=service_order
        )

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
            service_order.status = ServiceOrderStatus.fechada
            service_order.closed_at = datetime.utcnow()
            service_order.invoice_number = form.invoice_number.data
            service_order.invoice_date = datetime.utcnow()
            service_order.invoice_amount = form.invoice_amount.data
            service_order.service_details = form.service_details.data
            
            # Create financial entry
            financial_entry = FinancialEntry(
                service_order_id=service_order.id,
                description=f"Pagamento OS #{service_order.id} - {service_order.client.name}",
                amount=form.invoice_amount.data,
                type=FinancialEntryType.entrada,
                created_by=current_user.id
            )
            
            db.session.add(financial_entry)
            db.session.commit()
            
            log_action(
                'Fechamento de OS',
                'service_order',
                service_order.id,
                f"OS {id} fechada com NF-e {form.invoice_number.data}"
            )
            
            flash('Ordem de serviço fechada com sucesso!', 'success')
            return redirect(url_for('view_service_order', id=id))
            
        return render_template(
            'service_orders/view.html',
            service_order=service_order,
            close_form=form
        )

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
            client = Client(
                name=form.name.data,
                document=form.document.data,
                email=form.email.data,
                phone=form.phone.data,
                address=form.address.data
            )
            
            db.session.add(client)
            db.session.commit()
            
            log_action(
                'Criação de Cliente',
                'client',
                client.id,
                f"Cliente {client.name} criado"
            )
            
            flash('Cliente cadastrado com sucesso!', 'success')
            return redirect(url_for('clients'))
            
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
        
        log_action(
            'Exclusão de Cliente',
            'client',
            id,
            f"Cliente {client_name} excluído"
        )
        
        flash('Cliente excluído com sucesso!', 'success')
        return redirect(url_for('clients'))

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
            equipment = Equipment(
                client_id=form.client_id.data,
                type=form.type.data,
                brand=form.brand.data,
                model=form.model.data,
                serial_number=form.serial_number.data,
                year=form.year.data
            )
            
            db.session.add(equipment)
            db.session.commit()
            
            log_action(
                'Criação de Equipamento',
                'equipment',
                equipment.id,
                f"Equipamento {equipment.type} criado para cliente {equipment.client.name}"
            )
            
            flash('Equipamento cadastrado com sucesso!', 'success')
            return redirect(url_for('equipment'))
            
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
        
        return render_template(
            'equipment/view.html',
            equipment=equipment,
            service_orders=service_orders
        )

    @app.route('/maquinarios/<int:id>/editar', methods=['GET', 'POST'])
    @login_required
    def edit_equipment(id):
        equipment = Equipment.query.get_or_404(id)
        form = EquipmentForm(obj=equipment)
        
        # Load clients for dropdown
        form.client_id.choices = [(c.id, c.name) for c in Client.query.order_by(Client.name).all()]
        
        if form.validate_on_submit():
            equipment.client_id = form.client_id.data
            equipment.type = form.type.data
            equipment.brand = form.brand.data
            equipment.model = form.model.data
            equipment.serial_number = form.serial_number.data
            equipment.year = form.year.data
            
            db.session.commit()
            
            log_action(
                'Edição de Equipamento',
                'equipment',
                equipment.id,
                f"Equipamento {equipment.type} atualizado"
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
    @app.route('/os/<int:id>/nfe')
    @login_required
    def view_invoice(id):
        service_order = ServiceOrder.query.get_or_404(id)
        
        # Check if order is closed
        if service_order.status != ServiceOrderStatus.fechada:
            flash('Esta OS ainda não foi fechada.', 'warning')
            return redirect(url_for('view_service_order', id=id))
            
        return render_template('invoices/view.html', service_order=service_order)

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
