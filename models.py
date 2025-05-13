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
    profile_image = db.Column(db.String(255), default='default_profile.svg')
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
    images = db.relationship('ServiceOrderImage', backref='service_order', lazy=True, cascade="all, delete-orphan")

class ServiceOrderImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_order_id = db.Column(db.Integer, db.ForeignKey('service_order.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(200))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ServiceOrderImage {self.filename}>'

class FinancialEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_order_id = db.Column(db.Integer, db.ForeignKey('service_order.id'))
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(Enum(FinancialEntryType), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    # Campos para relacionar com outros tipos de entidades (pedidos a fornecedores, etc.)
    entry_type = db.Column(db.String(50))  # 'service_order', 'pedido_fornecedor', etc.
    reference_id = db.Column(db.Integer)   # ID da entidade referenciada

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

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    document = db.Column(db.String(18), unique=True)  # CPF or CNPJ
    contact_name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    website = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    parts = db.relationship('Part', backref='supplier', lazy=True)
    orders = db.relationship('SupplierOrder', backref='supplier', lazy=True)
    
class Part(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    part_number = db.Column(db.String(50))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    category = db.Column(db.String(50))
    subcategory = db.Column(db.String(50))
    cost_price = db.Column(db.Numeric(10, 2))  # Preço de custo
    selling_price = db.Column(db.Numeric(10, 2))  # Preço de venda
    stock_quantity = db.Column(db.Integer, default=0)
    minimum_stock = db.Column(db.Integer, default=0)
    location = db.Column(db.String(50))  # Localização no estoque/almoxarifado
    image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    sales = db.relationship('PartSale', backref='part', lazy=True)
    order_items = db.relationship('OrderItem', backref='part', lazy=True)

class PartSale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    service_order_id = db.Column(db.Integer, db.ForeignKey('service_order.id'))
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)  # Preço unitário na venda
    total_price = db.Column(db.Numeric(10, 2), nullable=False)  # Preço total (quantidade * preço unitário)
    sale_date = db.Column(db.DateTime, default=datetime.utcnow)
    invoice_number = db.Column(db.String(20))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OrderStatus(enum.Enum):
    pendente = "pendente"
    aprovado = "aprovado"
    enviado = "enviado"
    recebido = "recebido"
    cancelado = "cancelado"
    
class StockItemType(enum.Enum):
    """Tipo de item no estoque"""
    epi = "EPI (Equipamento de Proteção Individual)"
    ferramenta = "Ferramenta"
    consumivel = "Material de Consumo"
    
class StockItemStatus(enum.Enum):
    """Status do item de estoque"""
    disponivel = "Disponível"
    baixo = "Estoque Baixo"
    esgotado = "Esgotado"
    vencido = "Vencido/Expirado"

class SupplierOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    order_number = db.Column(db.String(50))
    total_value = db.Column(db.Numeric(10, 2))
    status = db.Column(Enum(OrderStatus), default=OrderStatus.pendente, nullable=False)
    expected_delivery_date = db.Column(db.Date)
    delivery_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    items = db.relationship('OrderItem', backref='supplier_order', lazy=True, cascade="all, delete-orphan")
    
class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('supplier_order.id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('part.id'))
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2))
    total_price = db.Column(db.Numeric(10, 2))
    status = db.Column(Enum(OrderStatus), default=OrderStatus.pendente, nullable=False)
    notes = db.Column(db.Text)
    
class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))

# Modelo para controle de sequências numéricas (NFe, OS, etc)
class SequenceCounter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    prefix = db.Column(db.String(10), nullable=True)
    current_value = db.Column(db.Integer, default=1, nullable=False)
    padding = db.Column(db.Integer, default=6, nullable=False)  # número de dígitos com zeros à esquerda
    description = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def next_value(self):
        """Incrementa e retorna o próximo valor da sequência"""
        self.current_value += 1
        db.session.commit()
        
        # Formatação com zeros à esquerda e prefixo, se existir
        formatted_number = str(self.current_value).zfill(self.padding)
        if self.prefix:
            return f"{self.prefix}{formatted_number}"
        return formatted_number
        
class StockItem(db.Model):
    """Modelo para itens de estoque (EPIs e ferramentas)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(Enum(StockItemType), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    min_quantity = db.Column(db.Integer, default=5)  # Quantidade mínima desejada em estoque
    location = db.Column(db.String(100), nullable=True)  # Localização física no depósito
    price = db.Column(db.Numeric(10, 2), nullable=True)  # Preço unitário
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    status = db.Column(Enum(StockItemStatus), default=StockItemStatus.disponivel)
    expiration_date = db.Column(db.Date, nullable=True)  # Data de validade (para EPIs)
    image = db.Column(db.String(255), nullable=True)  # Caminho para imagem do item
    ca_number = db.Column(db.String(50), nullable=True)  # Número do CA para EPIs
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relações
    supplier = db.relationship('Supplier', backref='stock_items')
    movements = db.relationship('StockMovement', backref='stock_item', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<StockItem {self.name}>'
        
    def update_status(self):
        """Atualiza o status do item com base na quantidade e data de validade"""
        today = datetime.now().date()
        
        if self.expiration_date and self.expiration_date <= today:
            self.status = StockItemStatus.vencido
        elif self.quantity <= 0:
            self.status = StockItemStatus.esgotado
        elif self.quantity <= self.min_quantity:
            self.status = StockItemStatus.baixo
        else:
            self.status = StockItemStatus.disponivel
        
        return self.status
        
class StockMovement(db.Model):
    """Registro de movimentações de estoque"""
    id = db.Column(db.Integer, primary_key=True)
    stock_item_id = db.Column(db.Integer, db.ForeignKey('stock_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)  # Positivo para entrada, negativo para saída
    description = db.Column(db.Text, nullable=True)
    reference = db.Column(db.String(100), nullable=True)  # Referência (número de OS, nome de funcionário, etc)
    service_order_id = db.Column(db.Integer, db.ForeignKey('service_order.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relações
    service_order = db.relationship('ServiceOrder', backref='stock_movements')
    
    def __repr__(self):
        return f'<StockMovement {self.id} - {self.quantity}>'
