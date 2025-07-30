"""
Performance utilities for SAMAPE application.
This module provides utilities to optimize database queries and improve performance.
"""
from sqlalchemy.orm import joinedload, selectinload
from database import db


def get_service_orders_with_relations(limit=None, offset=None, filters=None):
    """
    Get service orders with related data using eager loading to avoid N+1 queries.
    
    Args:
        limit: Maximum number of records to return
        offset: Number of records to skip
        filters: Dictionary of filters to apply
    
    Returns:
        Query object with optimized joins
    """
    from models import ServiceOrder, Client, User, Equipment
    
    query = ServiceOrder.query.options(
        joinedload(ServiceOrder.client),
        joinedload(ServiceOrder.responsible),
        selectinload(ServiceOrder.equipment),
        selectinload(ServiceOrder.financial_entries)
    )
    
    # Apply filters if provided
    if filters:
        if filters.get('status'):
            query = query.filter(ServiceOrder.status == filters['status'])
        if filters.get('client_id'):
            query = query.filter(ServiceOrder.client_id == filters['client_id'])
        if filters.get('responsible_id'):
            query = query.filter(ServiceOrder.responsible_id == filters['responsible_id'])
        if filters.get('date_from'):
            query = query.filter(ServiceOrder.created_at >= filters['date_from'])
        if filters.get('date_to'):
            query = query.filter(ServiceOrder.created_at <= filters['date_to'])
    
    query = query.order_by(ServiceOrder.created_at.desc())
    
    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)
    
    return query


def get_clients_with_equipment_count():
    """Get clients with equipment count using a single query."""
    from models import Client, Equipment
    from sqlalchemy import func
    
    return db.session.query(
        Client,
        func.count(Equipment.id).label('equipment_count')
    ).outerjoin(Equipment).group_by(Client.id).all()


def get_financial_summary_optimized(month=None, year=None):
    """Get financial summary with optimized query."""
    from models import FinancialEntry, FinancialEntryType
    from sqlalchemy import func, extract
    
    query = db.session.query(
        FinancialEntry.type,
        func.sum(FinancialEntry.amount).label('total')
    )
    
    if month and year:
        query = query.filter(
            extract('month', FinancialEntry.date) == month,
            extract('year', FinancialEntry.date) == year
        )
    elif year:
        query = query.filter(extract('year', FinancialEntry.date) == year)
    
    results = query.group_by(FinancialEntry.type).all()
    
    summary = {'income': 0, 'expenses': 0, 'balance': 0}
    
    for entry_type, total in results:
        if entry_type == FinancialEntryType.entrada:
            summary['income'] = float(total or 0)
        elif entry_type == FinancialEntryType.saida:
            summary['expenses'] = float(total or 0)
    
    summary['balance'] = summary['income'] - summary['expenses']
    return summary


def get_low_stock_items_optimized():
    """Get low stock items with supplier information."""
    from models import StockItem, Supplier
    
    return StockItem.query.options(
        joinedload(StockItem.supplier)
    ).filter(
        StockItem.quantity <= StockItem.min_quantity
    ).order_by(StockItem.quantity.asc()).all()


def get_parts_with_low_stock_optimized():
    """Get parts with low stock including supplier information."""
    from models import Part, Supplier
    
    return Part.query.options(
        joinedload(Part.supplier)
    ).filter(
        Part.stock_quantity <= Part.minimum_stock
    ).order_by(Part.stock_quantity.asc()).all()


def batch_update_stock_status():
    """Update stock status for all items in batches to improve performance."""
    from models import StockItem
    
    # Process in batches of 100
    batch_size = 100
    offset = 0
    
    while True:
        items = StockItem.query.offset(offset).limit(batch_size).all()
        if not items:
            break
        
        for item in items:
            item.update_status()
        
        db.session.commit()
        offset += batch_size


def get_dashboard_data_optimized():
    """Get all dashboard data in optimized queries."""
    from models import (
        ServiceOrder, ServiceOrderStatus, SupplierOrder, OrderStatus,
        Vehicle, VehicleStatus, ActionLog, StockItem, Part
    )
    from sqlalchemy import func
    
    # Service Order statistics
    so_stats = db.session.query(
        ServiceOrder.status,
        func.count(ServiceOrder.id).label('count')
    ).group_by(ServiceOrder.status).all()
    
    # Supplier Order statistics  
    supplier_stats = db.session.query(
        SupplierOrder.status,
        func.count(SupplierOrder.id).label('count')
    ).group_by(SupplierOrder.status).all()
    
    # Vehicle statistics
    vehicle_stats = db.session.query(
        Vehicle.status,
        func.count(Vehicle.id).label('count')
    ).group_by(Vehicle.status).all()
    
    # Recent orders with client info
    recent_orders = ServiceOrder.query.options(
        joinedload(ServiceOrder.client)
    ).order_by(ServiceOrder.created_at.desc()).limit(5).all()
    
    # Recent logs with user info
    recent_logs = ActionLog.query.options(
        joinedload(ActionLog.user)
    ).order_by(ActionLog.timestamp.desc()).limit(10).all()
    
    # Low stock counts
    low_stock_items_count = StockItem.query.filter(
        StockItem.quantity <= StockItem.min_quantity
    ).count()
    
    low_stock_parts_count = Part.query.filter(
        Part.stock_quantity <= Part.minimum_stock
    ).count()
    
    return {
        'service_orders': dict(so_stats),
        'supplier_orders': dict(supplier_stats),
        'vehicles': dict(vehicle_stats),
        'recent_orders': recent_orders,
        'recent_logs': recent_logs,
        'low_stock_items_count': low_stock_items_count,
        'low_stock_parts_count': low_stock_parts_count
    }
