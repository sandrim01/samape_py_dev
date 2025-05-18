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
    
class VehicleStatus(enum.Enum):
    ativo = "Ativo"
    em_manutencao = "Em Manutenção"  # Atualizado para corresponder ao banco de dados
    inativo = "Inativo"
    # reservado removido - não existe no banco de dados
    
class VehicleType(enum.Enum):
    carro = "Carro"
    caminhao = "Caminhão"
    van = "Van"
    onibus = "Ônibus"
    maquinario = "Maquinário"
    outro = "Outro"

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
    equipment = db.relationship('Equipment', secondary=equipment_service_orders, lazy='subquery', 
                               backref=db.backref('service_orders', lazy=True))

class ServiceOrderImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_order_id = db.Column(db.Integer, db.ForeignKey('service_order.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(200))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    # Campos adicionados para armazenar a imagem diretamente no banco de dados
    image_data = db.Column(db.LargeBinary)  # Dados binários da imagem
    mimetype = db.Column(db.String(100))    # Tipo MIME da imagem (ex: image/jpeg)
    file_size = db.Column(db.Integer)       # Tamanho do arquivo em bytes
    
    def __repr__(self):
        return f'<ServiceOrderImage {self.filename}>'
        
    @property
    def size_in_kb(self):
        """Retorna o tamanho da imagem em KB"""
        if self.file_size:
            return self.file_size / 1024
        return 0

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
    part_order_items = db.relationship('OrderItem', foreign_keys='OrderItem.part_id', lazy=True)

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
    stock_item_id = db.Column(db.Integer, db.ForeignKey('stock_item.id'))
    description = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2))
    total_price = db.Column(db.Numeric(10, 2))
    status = db.Column(Enum(OrderStatus), default=OrderStatus.pendente, nullable=False)
    notes = db.Column(db.Text)
    
    # Relacionamentos sem backref para evitar conflitos
    part = db.relationship('Part', foreign_keys=[part_id], overlaps="part_order_items")
    stock_item = db.relationship('StockItem', foreign_keys=[stock_item_id])
    
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
    stock_order_items = db.relationship('OrderItem', foreign_keys='OrderItem.stock_item_id', lazy=True, overlaps="stock_item")
    
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
    user = db.relationship('User', backref='stock_movements')
    
    def __repr__(self):
        return f'<StockMovement {self.id} - {self.quantity}>'
        
    def get_creator(self):
        """Retorna o usuário que criou o movimento"""
        if self.created_by:
            return User.query.get(self.created_by)
        return None

class FuelType(enum.Enum):
    """Tipo de combustível"""
    gasolina = "Gasolina"
    etanol = "Etanol"
    diesel = "Diesel"
    flex = "Flex (Gasolina/Etanol)"
    hibrido = "Híbrido"
    eletrico = "Elétrico"
    outro = "Outro"

class Vehicle(db.Model):
    """Modelo para veículos da frota"""
    id = db.Column(db.Integer, primary_key=True)
    # Não adicionar type aqui - coluna não existe no banco de dados
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    year = db.Column(db.Integer)
    plate = db.Column(db.String(20))  # Placa
    color = db.Column(db.String(50))
    chassis = db.Column(db.String(50))
    renavam = db.Column(db.String(50))
    fuel_type = db.Column(Enum(FuelType), default=FuelType.flex)
    acquisition_date = db.Column(db.Date)  # Data de aquisição
    insurance_policy = db.Column(db.String(50))  # Número da apólice de seguro
    insurance_expiry = db.Column(db.Date)  # Data de vencimento do seguro
    current_km = db.Column(db.Integer)  # Quilometragem atual
    next_maintenance_date = db.Column(db.Date)  # Data da próxima manutenção
    next_maintenance_km = db.Column(db.Integer)  # Km para próxima manutenção
    responsible_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(Enum(VehicleStatus), default=VehicleStatus.ativo, nullable=False)
    image = db.Column(db.String(255))  # Caminho da imagem
    notes = db.Column(db.Text)  # Observações
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    responsible = db.relationship('User', backref='vehicles', foreign_keys=[responsible_id])
    maintenance_history = db.relationship('VehicleMaintenance', backref='vehicle', lazy=True, cascade="all, delete-orphan")
    refuelings = db.relationship('Refueling', back_populates='vehicle', lazy=True, cascade="all, delete-orphan")
    travel_logs = db.relationship('VehicleTravelLog', back_populates='vehicle', lazy=True, cascade="all, delete-orphan")
    
    @property
    def identifier(self):
        """Retorna a placa como identificador do veículo"""
        return self.plate or f"{self.brand} {self.model} ({self.id})"
    
    @property
    def mileage(self):
        """Compatibilidade para templates existentes"""
        return self.current_km
    
    @property
    def purchase_date(self):
        """Compatibilidade para templates existentes"""
        return self.acquisition_date
        
    @property
    def license_plate(self):
        """Compatibilidade para templates existentes"""
        return self.plate
    
    def __repr__(self):
        return f'<Vehicle {self.plate} - {self.brand} {self.model}>'

class MaintenanceType(enum.Enum):
    """Tipo de manutenção"""
    preventiva = "Preventiva"
    corretiva = "Corretiva"
    revisao = "Revisão"
    outra = "Outra"

class VehicleMaintenance(db.Model):
    """Registro de manutenções realizadas nos veículos"""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    odometer = db.Column(db.Integer)  # Odômetro na data da manutenção
    description = db.Column(db.Text, nullable=False)
    maintenance_type = db.Column(Enum(MaintenanceType), default=MaintenanceType.revisao)
    completed = db.Column(db.Boolean, default=True)  # Se a manutenção foi concluída
    cost = db.Column(db.Float)  # Custo da manutenção
    workshop = db.Column(db.String(100))  # Oficina/local onde foi realizada
    invoice_number = db.Column(db.String(50))  # Número da nota fiscal
    invoice_image = db.Column(db.String(255))  # Imagem da nota fiscal
    service_order_id = db.Column(db.Integer, db.ForeignKey('service_order.id'))  # OS relacionada
    next_maintenance_date = db.Column(db.Date)  # Data da próxima manutenção
    next_maintenance_km = db.Column(db.Integer)  # Km para próxima manutenção
    notes = db.Column(db.Text)  # Observações adicionais
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    service_order = db.relationship('ServiceOrder', backref='vehicle_maintenance')
    creator = db.relationship('User', backref='maintenance_created', foreign_keys=[created_by])
    
    @property
    def mileage(self):
        """Compatibilidade para templates existentes"""
        return self.odometer
        
    @property
    def service_provider(self):
        """Compatibilidade para templates existentes"""
        return self.workshop
        
    @property
    def performed_by(self):
        """Compatibilidade para templates existentes"""
        if self.created_by:
            return User.query.get(self.created_by)
        return None
    
    def __repr__(self):
        return f'<VehicleMaintenance {self.id} - {self.date}>'
        
        
class Refueling(db.Model):
    """Registros de abastecimento de veículos"""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)  # Data do abastecimento
    odometer = db.Column(db.Integer)  # Hodômetro na data do abastecimento
    fuel_type = db.Column(Enum(FuelType), default=FuelType.flex)  # Tipo de combustível
    liters = db.Column(db.Float)  # Quantidade em litros
    price_per_liter = db.Column(db.Float)  # Preço por litro
    total_cost = db.Column(db.Float)  # Custo total
    full_tank = db.Column(db.Boolean, default=False)  # Tanque completo
    gas_station = db.Column(db.String(100))  # Posto de combustível
    receipt_image = db.Column(db.String(255))  # Imagem do comprovante
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Motorista
    service_order_id = db.Column(db.Integer, db.ForeignKey('service_order.id'))  # OS relacionada
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Quem criou o registro
    notes = db.Column(db.Text)  # Observações
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Data de criação
    
    # Relationships
    vehicle = db.relationship('Vehicle', back_populates='refuelings', foreign_keys=[vehicle_id])
    service_order = db.relationship('ServiceOrder', backref='refuelings')
    driver = db.relationship('User', backref='refuelings_as_driver', foreign_keys=[driver_id])
    creator = db.relationship('User', backref='refuelings_created', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<Refueling {self.id} - {self.date}>'
        
        
class VehicleTravelLog(db.Model):
    """Registro de viagens/deslocamentos de veículos"""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Motorista
    start_date = db.Column(db.DateTime, nullable=False)  # Data/hora de início
    end_date = db.Column(db.DateTime)  # Data/hora de término
    start_odometer = db.Column(db.Integer)  # Hodômetro de início
    end_odometer = db.Column(db.Integer)  # Hodômetro de término
    distance = db.Column(db.Float)  # Distância percorrida
    destination = db.Column(db.String(255))  # Destino
    purpose = db.Column(db.Text)  # Finalidade da viagem
    service_order_id = db.Column(db.Integer, db.ForeignKey('service_order.id'))  # OS relacionada
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Quem criou o registro
    notes = db.Column(db.Text)  # Observações
    status = db.Column(db.String(20), default='concluído')  # Status: em andamento, concluído, cancelado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Data de criação
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Data de atualização
    
    # Relationships
    vehicle = db.relationship('Vehicle', back_populates='travel_logs', foreign_keys=[vehicle_id])
    service_order = db.relationship('ServiceOrder', backref='vehicle_travel_logs')
    driver = db.relationship('User', backref='travel_logs_as_driver', foreign_keys=[driver_id])
    creator = db.relationship('User', backref='travel_logs_created', foreign_keys=[created_by])
    
    def __repr__(self):
        return f'<VehicleTravelLog {self.id} - {self.destination}>'
