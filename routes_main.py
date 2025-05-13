"""
Módulo para as rotas principais do sistema (dashboard, ordens de serviço, vendas, notas fiscais)
"""
import os
from datetime import datetime, timedelta
from sqlalchemy import func, desc, or_
from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user

from app import db
from models import (
    User, Client, Equipment, ServiceOrder, FinancialEntry, PartSale,
    UserRole, ServiceOrderStatus, FinancialEntryType, Part, 
    StockItem, StockMovement, Vehicle, Refueling, VehicleMaintenance
)
from utils import get_system_setting, log_action, get_monthly_summary, get_service_order_stats
from utils import format_currency, format_document, get_supplier_order_stats
from utils import get_maintenance_in_progress
from forms import (
    ServiceOrderForm, CloseServiceOrderForm, FinancialEntryForm, PartSaleForm
)

# Rota do Dashboard
@login_required
def dashboard():
    """Página inicial/dashboard do sistema"""
    # Estatísticas gerais
    total_orders = ServiceOrder.query.count()
    open_orders = ServiceOrder.query.filter_by(status=ServiceOrderStatus.aberta).count()
    in_progress_orders = ServiceOrder.query.filter_by(status=ServiceOrderStatus.em_andamento).count()
    completed_orders = ServiceOrder.query.filter_by(status=ServiceOrderStatus.fechada).count()
    
    total_clients = Client.query.count()
    total_equipment = Equipment.query.count()
    
    # Resumo financeiro do mês atual
    financial_summary = get_monthly_summary()
    
    # Últimas ordens de serviço
    recent_orders = ServiceOrder.query.order_by(ServiceOrder.created_at.desc()).limit(5).all()
    
    # Estatísticas de ordens de serviço
    service_order_stats = get_service_order_stats()
    
    # Estatísticas de pedidos a fornecedores
    supplier_order_stats = get_supplier_order_stats()
    
    # Manutenções em andamento
    maintenance_in_progress = get_maintenance_in_progress()
    
    # Movimentos de estoque recentes
    recent_stock_movements = StockMovement.query.order_by(StockMovement.created_at.desc()).limit(5).all()
    
    # Abastecimentos recentes
    recent_refuelings = Refueling.query.order_by(Refueling.date.desc()).limit(5).all()
    
    # Manutenções recentes
    recent_maintenance = VehicleMaintenance.query.order_by(VehicleMaintenance.date.desc()).limit(5).all()
    
    return render_template(
        'dashboard.html',
        title='Dashboard',
        total_orders=total_orders,
        open_orders=open_orders,
        in_progress_orders=in_progress_orders,
        completed_orders=completed_orders,
        total_clients=total_clients,
        total_equipment=total_equipment,
        financial_summary=financial_summary,
        recent_orders=recent_orders,
        service_order_stats=service_order_stats,
        supplier_order_stats=supplier_order_stats,
        maintenance_in_progress=maintenance_in_progress,
        recent_stock_movements=recent_stock_movements,
        recent_refuelings=recent_refuelings,
        recent_maintenance=recent_maintenance
    )

# Rotas de Ordens de Serviço
@login_required
def service_orders():
    """Lista todas as ordens de serviço com opções de filtro"""
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
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        query = query.filter(ServiceOrder.created_at >= date_from)
    
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        date_to = date_to + timedelta(days=1)  # Include the end date
        query = query.filter(ServiceOrder.created_at < date_to)
    
    # Get all service orders sorted by creation date (newest first)
    service_orders = query.order_by(ServiceOrder.created_at.desc()).all()
    
    # Get clients and responsibles for filter options
    clients = Client.query.order_by(Client.name).all()
    responsibles = User.query.order_by(User.name).all()
    
    return render_template(
        'service_orders/index.html',
        title='Ordens de Serviço',
        service_orders=service_orders,
        clients=clients,
        responsibles=responsibles,
        status_filter=status_filter,
        client_filter=client_filter,
        responsible_filter=responsible_filter,
        date_from=date_from if isinstance(date_from, str) else date_from.strftime('%Y-%m-%d') if date_from else '',
        date_to=date_to if isinstance(date_to, str) else (date_to - timedelta(days=1)).strftime('%Y-%m-%d') if date_to else ''
    )

# Rota de Vendas de Peças
@login_required
def part_sales():
    """Lista todas as vendas de peças"""
    # Filtros
    client_filter = request.args.get('client', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = PartSale.query
    
    # Aplicar filtros
    if client_filter:
        query = query.filter(PartSale.client_id == client_filter)
        
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        query = query.filter(PartSale.date >= date_from)
    
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        date_to = date_to + timedelta(days=1)  # Incluir o dia final
        query = query.filter(PartSale.date < date_to)
    
    # Obter todas as vendas ordenadas por data (mais recentes primeiro)
    sales = query.order_by(PartSale.date.desc()).all()
    
    # Obter clientes para opções de filtro
    clients = Client.query.order_by(Client.name).all()
    
    # Calcular totais
    total_amount = sum(sale.total_price for sale in sales)
    
    return render_template(
        'parts/sales/index.html',
        title='Vendas de Peças',
        sales=sales,
        clients=clients,
        client_filter=client_filter,
        date_from=date_from if isinstance(date_from, str) else date_from.strftime('%Y-%m-%d') if date_from else '',
        date_to=date_to if isinstance(date_to, str) else (date_to - timedelta(days=1)).strftime('%Y-%m-%d') if date_to else '',
        total_amount=total_amount
    )

# Rotas de Notas Fiscais
@login_required
def invoices():
    """Lista todas as notas fiscais"""
    # Filtros
    client_filter = request.args.get('client', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    service_order_filter = request.args.get('service_order', '')
    
    # Inicializar consulta para notas fiscais (com base em ordens de serviço)
    query = ServiceOrder.query.filter(ServiceOrder.invoice_number != None, ServiceOrder.invoice_number != '')
    
    # Aplicar filtros
    if client_filter:
        query = query.filter(ServiceOrder.client_id == client_filter)
    
    if service_order_filter:
        query = query.filter(ServiceOrder.id == service_order_filter)
    
    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        query = query.filter(ServiceOrder.invoice_date >= date_from)
    
    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        date_to = date_to + timedelta(days=1)  # Incluir o dia final
        query = query.filter(ServiceOrder.invoice_date < date_to)
    
    # Obter notas fiscais ordenadas por data (mais recentes primeiro)
    invoices = query.order_by(ServiceOrder.invoice_date.desc()).all()
    
    # Obter clientes e ordens de serviço para opções de filtro
    clients = Client.query.order_by(Client.name).all()
    service_orders = ServiceOrder.query.filter(
        ServiceOrder.invoice_number != None, 
        ServiceOrder.invoice_number != ''
    ).order_by(ServiceOrder.number.desc()).all()
    
    return render_template(
        'invoices/index.html',
        title='Notas Fiscais',
        invoices=invoices,
        clients=clients,
        service_orders=service_orders,
        client_filter=client_filter,
        service_order_filter=service_order_filter,
        date_from=date_from if isinstance(date_from, str) else date_from.strftime('%Y-%m-%d') if date_from else '',
        date_to=date_to if isinstance(date_to, str) else (date_to - timedelta(days=1)).strftime('%Y-%m-%d') if date_to else ''
    )