import enum
from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import Enum
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

# Enum definitions
class UserRole(enum.Enum):
    admin = "admin"
    gerente = "gerente"
    funcionario = "funcionario"

class ServiceOrderStatus(enum.Enum):
    aberta = "aberta"
    em_andamento = "em_andamento"
    fechada = "fechada"

class FinancialEntryType(enum.Enum):
    entrada = "entrada"
    saida = "saida"

# Association tables
equipment_service_orders = db.Table(
    'equipment_service_orders',
    db.Column('equipment_id', db.Integer, db.ForeignKey('equipment.id'), primary_key=True),
    db.Column('service_order_id', db.Integer, db.ForeignKey('service_order.id'), primary_key=True)
)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(Enum(UserRole), default=UserRole.funcionario, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    service_orders = db.relationship('ServiceOrder', backref='responsible', lazy=True)
    logs = db.relationship('ActionLog', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == UserRole.admin
    
    def is_manager(self):
        return self.role == UserRole.gerente
    
    def is_employee(self):
        return self.role == UserRole.funcionario

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    document = db.Column(db.String(18), unique=True, nullable=False)  # CPF or CNPJ
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    equipment = db.relationship('Equipment', backref='client', lazy=True)
    service_orders = db.relationship('ServiceOrder', backref='client', lazy=True)

class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50))
    model = db.Column(db.String(50))
    serial_number = db.Column(db.String(50), unique=True)
    year = db.Column(db.Integer)
    last_maintenance = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    service_orders = db.relationship('ServiceOrder', secondary=equipment_service_orders, backref=db.backref('equipment', lazy=True))
    
class ServiceOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    responsible_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    description = db.Column(db.Text, nullable=False)
    estimated_value = db.Column(db.Numeric(10, 2), nullable=True)  # Valor estimado da OS
    status = db.Column(Enum(ServiceOrderStatus), default=ServiceOrderStatus.aberta, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    
    # Invoice information (filled when closed)
    invoice_number = db.Column(db.String(20))
    invoice_date = db.Column(db.DateTime)
    invoice_amount = db.Column(db.Numeric(10, 2))
    service_details = db.Column(db.Text)
    
    # Relations
    financial_entries = db.relationship('FinancialEntry', backref='service_order', lazy=True)

class FinancialEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_order_id = db.Column(db.Integer, db.ForeignKey('service_order.id'))
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(Enum(FinancialEntryType), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class ActionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(200), nullable=False)
    entity_type = db.Column(db.String(50))  # 'user', 'client', 'equipment', 'service_order', 'financial'
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class LoginAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)  # Esta é a coluna que existe no banco de dados
    success = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
