from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, DecimalField, HiddenField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError, NumberRange, Regexp
import re
from datetime import datetime
from models import User, Client, ServiceOrderStatus, UserRole, FinancialEntryType, Supplier, Part, OrderStatus, StockItemType, StockItemStatus, StockItem, ServiceOrder, VehicleType, VehicleStatus, Vehicle, FuelType, MaintenanceType

class DeleteImageForm(FlaskForm):
    """Formulário simples para exclusão de imagens"""
    pass

class LoginForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')

class UserForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=3, max=64)])
    name = StringField('Nome', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Função', choices=[(role.name, role.value) for role in UserRole], validators=[DataRequired()])
    password = PasswordField('Senha', validators=[
        Optional(),
        Length(min=8, message='A senha deve ter pelo menos 8 caracteres')
    ])
    confirm_password = PasswordField('Confirmar Senha', validators=[
        EqualTo('password', message='As senhas devem ser iguais')
    ])
    active = BooleanField('Ativo', default=True)
    
    # Armazenar um ID de usuário para checagem de duplicatas
    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop('user_id', None)
        super(UserForm, self).__init__(*args, **kwargs)
    
    def validate_username(self, field):
        if self.user_id is None:  # Novo usuário
            if User.query.filter_by(username=field.data).first():
                raise ValidationError('Este nome de usuário já está em uso.')
        else:  # Usuário existente
            user = User.query.filter_by(username=field.data).first()
            if user and user.id != self.user_id:
                raise ValidationError('Este nome de usuário já está em uso.')
    
    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user and user.id != getattr(self, 'user_id', None):
            raise ValidationError('Este email já está em uso.')

class ProfileForm(FlaskForm):
    name = StringField('Nome', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    profile_image = FileField('Foto de Perfil', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Apenas imagens são permitidas!')
    ])
    current_password = PasswordField('Senha Atual', validators=[Optional()])
    new_password = PasswordField('Nova Senha', validators=[
        Optional(),
        Length(min=8, message='A senha deve ter pelo menos 8 caracteres'),
        Regexp(r'(?=.*\d)(?=.*[a-z])(?=.*[A-Z])', 
               message='A senha deve conter pelo menos um número, uma letra minúscula e uma letra maiúscula')
    ])
    confirm_password = PasswordField('Confirmar Nova Senha', validators=[
        EqualTo('new_password', message='As senhas devem ser iguais')
    ])

class ClientForm(FlaskForm):
    name = StringField('Nome/Razão Social', validators=[DataRequired(), Length(min=3, max=100)])
    document = StringField('CPF/CNPJ', validators=[DataRequired(), Length(min=11, max=18)])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    address = StringField('Endereço', validators=[Optional(), Length(max=200)])
    
    def validate_document(self, field):
        # Remove special characters
        doc = re.sub(r'[^0-9]', '', field.data)
        
        # Check if it's a CPF (11 digits) or CNPJ (14 digits)
        if len(doc) != 11 and len(doc) != 14:
            raise ValidationError('CPF deve ter 11 dígitos e CNPJ deve ter 14 dígitos.')
        
        # Check if document already exists
        client = Client.query.filter_by(document=doc).first()
        if client and client.id != getattr(self, 'client_id', None):
            raise ValidationError('Este documento já está cadastrado.')
        
        # Format data to store in standard format
        field.data = doc

class EquipmentForm(FlaskForm):
    client_id = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    type_select = SelectField('Tipo', validators=[Optional()], default='')
    type = StringField('Outro Tipo (se não estiver na lista)', validators=[Optional(), Length(max=50)])
    brand_select = SelectField('Marca', validators=[Optional()], default='')
    brand = StringField('Outra Marca (se não estiver na lista)', validators=[Optional(), Length(max=50)])
    model_select = SelectField('Modelo', validators=[Optional()], default='')
    model = StringField('Outro Modelo (se não estiver na lista)', validators=[Optional(), Length(max=50)])
    serial_number = StringField('Número de Série', validators=[DataRequired(), Length(max=50)])
    year = StringField('Ano', validators=[Optional(), Length(max=4)])
    
    def __init__(self, *args, **kwargs):
        super(EquipmentForm, self).__init__(*args, **kwargs)
        # Preencher os SelectFields com opções do banco de dados
        from models import Equipment
        from sqlalchemy import distinct
        from app import db
        
        # Inicializar os campos de seleção com valores padrão para evitar erros
        self.type_select.choices = [('', 'Selecione um tipo')]
        self.brand_select.choices = [('', 'Selecione uma marca')]
        self.model_select.choices = [('', 'Selecione um modelo')]
        
        try:
            # Obter marcas distintas
            brands = db.session.query(distinct(Equipment.brand)).order_by(Equipment.brand).all()
            brand_choices = [(b[0], b[0]) for b in brands if b[0] is not None]
            if brand_choices:
                self.brand_select.choices = [('', 'Selecione uma marca')] + brand_choices
            
            # Obter tipos distintos
            types = db.session.query(distinct(Equipment.type)).order_by(Equipment.type).all()
            type_choices = [(t[0], t[0]) for t in types if t[0] is not None]
            if type_choices:
                self.type_select.choices = [('', 'Selecione um tipo')] + type_choices
        except Exception:
            # Em caso de erro, manter as opções padrão
            pass
        
        # Modelo será preenchido via AJAX com base na marca selecionada

class ServiceOrderForm(FlaskForm):
    client_id = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    equipment_ids = HiddenField('Equipamentos', validators=[Optional()])
    responsible_id = SelectField('Responsável', coerce=int, validators=[Optional()])
    description = TextAreaField('Descrição do Serviço', validators=[DataRequired()])
    estimated_value = DecimalField('Valor Estimado (R$)', validators=[Optional()], places=2)
    invoice_amount = DecimalField('Valor Total da Nota (R$)', validators=[Optional()], places=2)
    status = SelectField('Status', choices=[(status.name, status.value) for status in ServiceOrderStatus], validators=[DataRequired()])
    images = FileField('Imagens do Equipamento', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Apenas imagens são permitidas!')
    ], render_kw={"multiple": True})
    image_descriptions = TextAreaField('Descrições das Imagens (separadas por ponto e vírgula)', validators=[Optional()])

class CloseServiceOrderForm(FlaskForm):
    # Removido campo invoice_number que agora será gerado automaticamente
    invoice_amount = DecimalField('Valor Total (R$)', validators=[DataRequired()], places=2)
    service_details = TextAreaField('Detalhes do Serviço Executado', validators=[DataRequired()])

class FinancialEntryForm(FlaskForm):
    service_order_id = SelectField('Ordem de Serviço', coerce=int, validators=[Optional()])
    description = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    amount = DecimalField('Valor (R$)', validators=[DataRequired()], places=2)
    type = SelectField('Tipo', choices=[(t.name, t.value) for t in FinancialEntryType], validators=[DataRequired()])
    date = StringField('Data', validators=[DataRequired()])

class SupplierForm(FlaskForm):
    name = StringField('Nome/Razão Social', validators=[DataRequired(), Length(min=3, max=100)])
    document = StringField('CPF/CNPJ', validators=[Optional(), Length(min=11, max=18)])
    contact_name = StringField('Nome do Contato', validators=[Optional(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    address = StringField('Endereço', validators=[Optional(), Length(max=200)])
    website = StringField('Website', validators=[Optional(), Length(max=100)])
    notes = TextAreaField('Observações', validators=[Optional()])
    id = HiddenField()
    
    def validate_document(self, field):
        if field.data:
            supplier = Supplier.query.filter_by(document=field.data).first()
            if supplier and (not self.id.data or supplier.id != int(self.id.data)):
                raise ValidationError('Este CPF/CNPJ já está cadastrado.')
    
    def __init__(self, *args, **kwargs):
        super(SupplierForm, self).__init__(*args, **kwargs)


class PartForm(FlaskForm):
    name = StringField('Nome da Peça', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Descrição', validators=[Optional()])
    part_number = StringField('Número da Peça', validators=[Optional(), Length(max=50)])
    supplier_id = SelectField('Fornecedor', validators=[Optional()], coerce=lambda x: int(x) if x else None)
    category = SelectField('Categoria', validators=[Optional()])
    subcategory = StringField('Subcategoria', validators=[Optional(), Length(max=50)])
    cost_price = DecimalField('Preço de Custo (R$)', validators=[Optional()], places=2)
    selling_price = DecimalField('Preço de Venda (R$)', validators=[Optional()], places=2)
    stock_quantity = IntegerField('Quantidade em Estoque', validators=[Optional()], default=0)
    minimum_stock = IntegerField('Estoque Mínimo', validators=[Optional()], default=0)
    location = StringField('Localização no Estoque', validators=[Optional(), Length(max=50)])
    image = FileField('Imagem da Peça', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens são permitidas!')
    ])
    id = HiddenField()
    
    def __init__(self, *args, **kwargs):
        super(PartForm, self).__init__(*args, **kwargs)
        # Fornecedores para o dropdown
        from models import Supplier
        self.supplier_id.choices = [('', 'Selecione um fornecedor')] + [
            (s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()
        ]
        
        # Categorias predefinidas para o dropdown
        self.category.choices = [('', 'Selecione uma categoria')] + [
            ('motor', 'Motor'),
            ('transmissao', 'Transmissão'),
            ('hidraulica', 'Sistema Hidráulico'),
            ('eletrica', 'Sistema Elétrico'),
            ('estrutura', 'Estrutura/Chassi'),
            ('rodante', 'Sistema Rodante'),
            ('limpeza', 'Limpeza/Manutenção'),
            ('vedacao', 'Vedação/Selagem'),
            ('perfuracao', 'Perfuração'),
            ('seguranca', 'Segurança'),
            ('outro', 'Outro')
        ]


class PartSaleForm(FlaskForm):
    part_id = SelectField('Peça', coerce=int, validators=[DataRequired()])
    client_id = SelectField('Cliente', validators=[Optional()], coerce=lambda x: int(x) if x else None)
    service_order_id = SelectField('Ordem de Serviço', validators=[Optional()], coerce=lambda x: int(x) if x else None)
    quantity = IntegerField('Quantidade', validators=[DataRequired(), NumberRange(min=1)], default=1)
    unit_price = DecimalField('Preço Unitário (R$)', validators=[DataRequired()], places=2)
    total_price = DecimalField('Preço Total (R$)', validators=[DataRequired()], places=2)
    invoice_number = StringField('Número da NF-e', validators=[Optional(), Length(max=20)])
    notes = TextAreaField('Observações', validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(PartSaleForm, self).__init__(*args, **kwargs)
        # Peças para o dropdown
        from models import Part
        part_choices = [(p.id, f"{p.name} - {p.part_number or 'S/N'} - R$ {p.selling_price or 0:.2f}") 
                       for p in Part.query.filter(Part.stock_quantity > 0).order_by(Part.name).all()]
        if part_choices:
            self.part_id.choices = part_choices
        else:
            self.part_id.choices = [(0, 'Nenhuma peça disponível em estoque')]
        
        # Clientes para o dropdown
        from models import Client
        self.client_id.choices = [('', 'Selecione um cliente')] + [
            (c.id, c.name) for c in Client.query.order_by(Client.name).all()
        ]
        
        # Ordens de serviço para o dropdown
        from models import ServiceOrder
        from models import ServiceOrderStatus
        self.service_order_id.choices = [('', 'Selecione uma OS')] + [
            (o.id, f"OS #{o.id} - {o.client.name}") 
            for o in ServiceOrder.query.filter(
                ServiceOrder.status != ServiceOrderStatus.fechada
            ).order_by(ServiceOrder.id.desc()).all()
        ]


class SupplierOrderForm(FlaskForm):
    supplier_id = SelectField('Fornecedor', validators=[DataRequired()], coerce=lambda x: int(x) if x else None)
    order_number = StringField('Número do Pedido', validators=[Optional(), Length(max=50)])
    total_value = DecimalField('Valor Total (R$)', validators=[Optional()], places=2)
    status = SelectField('Status', choices=[(status.name, status.value) for status in OrderStatus], validators=[DataRequired()])
    expected_delivery_date = StringField('Data Prevista de Entrega', validators=[Optional()])
    delivery_date = StringField('Data de Entrega', validators=[Optional()])
    notes = TextAreaField('Observações', validators=[Optional()])
    id = HiddenField()

    def __init__(self, *args, **kwargs):
        super(SupplierOrderForm, self).__init__(*args, **kwargs)
        # Fornecedores para o dropdown
        from models import Supplier
        self.supplier_id.choices = [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()]


class OrderItemForm(FlaskForm):
    stock_item_id = SelectField('Item de Estoque', validators=[Optional()], coerce=lambda x: int(x) if x else None)
    description = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    quantity = IntegerField('Quantidade', validators=[DataRequired(), NumberRange(min=1)], default=1)
    unit_price = DecimalField('Preço Unitário (R$)', validators=[Optional()], places=2)
    total_price = DecimalField('Preço Total (R$)', validators=[Optional()], places=2)
    status = SelectField('Status', choices=[(status.name, status.value) for status in OrderStatus], validators=[DataRequired()])
    notes = TextAreaField('Observações', validators=[Optional()])
    id = HiddenField()

    def __init__(self, *args, **kwargs):
        super(OrderItemForm, self).__init__(*args, **kwargs)
        # Itens de estoque para o dropdown (EPIs, ferramentas e material de consumo)
        from models import StockItem
        self.stock_item_id.choices = [('', 'Selecione um item de estoque ou digite a descrição')] + [
            (item.id, f"{item.name} - {item.type.value} - {item.quantity} em estoque") 
            for item in StockItem.query.order_by(StockItem.name).all()
        ]


class SystemSettingsForm(FlaskForm):
    theme = SelectField('Tema', choices=[
        ('light', 'Claro'),
        ('dark', 'Escuro'),
        ('auto', 'Automático (Usar Configuração do Sistema)')
    ], validators=[DataRequired()])
    timezone = SelectField('Fuso Horário', choices=[
        ('America/Sao_Paulo', 'Brasília (GMT-3)'),
        ('America/Manaus', 'Manaus (GMT-4)'),
        ('America/Cuiaba', 'Cuiabá (GMT-4)'),
        ('America/Rio_Branco', 'Rio Branco (GMT-5)')
    ], validators=[DataRequired()])
    date_format = SelectField('Formato de Data', choices=[
        ('DD/MM/YYYY', 'DD/MM/AAAA (ex: 31/12/2023)'),
        ('MM/DD/YYYY', 'MM/DD/AAAA (ex: 12/31/2023)'),
        ('YYYY-MM-DD', 'AAAA-MM-DD (ex: 2023-12-31)')
    ], validators=[DataRequired()])
    items_per_page = SelectField('Itens por Página', coerce=int, choices=[
        (10, '10'),
        (20, '20'),
        (50, '50'),
        (100, '100')
    ], validators=[DataRequired()])
    
class VehicleForm(FlaskForm):
    """Formulário para cadastro e edição de veículos da frota"""
    # Campo type removido - não existe na tabela
    plate = StringField('Placa *', validators=[DataRequired(), Length(max=20)])
    brand = StringField('Marca', validators=[Optional(), Length(max=50)])
    model = StringField('Modelo', validators=[Optional(), Length(max=100)])
    year = IntegerField('Ano', validators=[Optional(), NumberRange(min=1950, max=datetime.now().year + 1)])
    color = StringField('Cor', validators=[Optional(), Length(max=50)])
    chassis = StringField('Chassi/Número de Série', validators=[Optional(), Length(max=50)])
    renavam = StringField('Renavam', validators=[Optional(), Length(max=50)])
    fuel_type = SelectField('Tipo de Combustível', choices=[(f.name, f.value) for f in FuelType], validators=[Optional()])
    acquisition_date = StringField('Data de Aquisição', validators=[Optional()], render_kw={"type": "date"})
    insurance_policy = StringField('Apólice de Seguro', validators=[Optional(), Length(max=50)])
    insurance_expiry = StringField('Vencimento do Seguro', validators=[Optional()], render_kw={"type": "date"})
    current_km = IntegerField('Hodômetro/Horímetro (Km)', validators=[Optional(), NumberRange(min=0)])
    next_maintenance_date = StringField('Data da Próxima Manutenção', validators=[Optional()], render_kw={"type": "date"})
    next_maintenance_km = IntegerField('Km para Próxima Manutenção', validators=[Optional(), NumberRange(min=0)])
    responsible_id = SelectField('Responsável', validators=[Optional()], coerce=lambda x: int(x) if x else None)
    status = SelectField('Status *', choices=[(s.name, s.value) for s in VehicleStatus], validators=[DataRequired()])
    image = FileField('Imagem do Veículo', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens são permitidas!')
    ])
    notes = TextAreaField('Observações', validators=[Optional(), Length(max=1000)])
    
    def __init__(self, *args, **kwargs):
        super(VehicleForm, self).__init__(*args, **kwargs)
        self.responsible_id.choices = [(0, 'Não atribuído')] + [
            (u.id, u.name) for u in User.query.filter_by(active=True).order_by(User.name).all()
        ]
        
class VehicleMaintenanceForm(FlaskForm):
    """Formulário para registro de manutenções nos veículos"""
    vehicle_id = SelectField('Veículo *', coerce=int, validators=[DataRequired()])
    date = StringField('Data *', validators=[DataRequired()])
    mileage = IntegerField('Hodômetro (Km)', validators=[Optional(), NumberRange(min=0)])
    description = TextAreaField('Descrição do Serviço *', validators=[DataRequired()])
    cost = DecimalField('Custo (R$)', validators=[Optional()], places=2)
    service_provider = StringField('Prestador do Serviço', validators=[Optional(), Length(max=100)])
    invoice_number = StringField('Número da NF', validators=[Optional(), Length(max=50)])
    performed_by_id = SelectField('Executado por', coerce=int, validators=[Optional()])
    
    def __init__(self, *args, **kwargs):
        super(VehicleMaintenanceForm, self).__init__(*args, **kwargs)
        # Usar o nome da coluna real em vez de property
        self.vehicle_id.choices = [(v.id, f"{v.plate} - {v.brand} {v.model}") 
                                 for v in Vehicle.query.order_by(Vehicle.id).all()]
        self.performed_by_id.choices = [(0, 'Não especificado')] + [
            (u.id, u.name) for u in User.query.filter_by(active=True).order_by(User.name).all()
        ]
        
class RefuelingForm(FlaskForm):
    """Formulário para registro de abastecimentos de veículos"""
    date = StringField('Data *', validators=[DataRequired()])
    odometer = IntegerField('Hodômetro (Km) *', validators=[DataRequired(), NumberRange(min=0)])
    fuel_type = SelectField('Tipo de Combustível *', choices=[
        ('gasolina', 'Gasolina'),
        ('diesel', 'Diesel'),
        ('etanol', 'Etanol'),
        ('flex', 'Flex (Misto)'),
        ('gnv', 'GNV')
    ], validators=[DataRequired()])
    liters = DecimalField('Quantidade (Litros) *', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    price_per_liter = DecimalField('Preço por Litro (R$) *', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    total_cost = DecimalField('Valor Total (R$) *', validators=[DataRequired(), NumberRange(min=0.01)], places=2)
    gas_station = StringField('Posto de Combustível', validators=[Optional(), Length(max=100)])
    full_tank = BooleanField('Tanque Completo', default=True)
    receipt_image = FileField('Comprovante', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'pdf'], 'Apenas imagens ou PDF são permitidos!')
    ])
    notes = TextAreaField('Observações', validators=[Optional(), Length(max=500)])
    
class StockItemForm(FlaskForm):
    """Formulário para cadastro e edição de itens de estoque"""
    name = StringField('Nome do Item', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Descrição', validators=[Optional()])
    type = SelectField('Tipo', choices=[(t.name, t.value) for t in StockItemType], validators=[DataRequired()])
    quantity = IntegerField('Quantidade em Estoque', validators=[DataRequired(), NumberRange(min=0)], default=0)
    min_quantity = IntegerField('Quantidade Mínima', validators=[DataRequired(), NumberRange(min=0)], default=5)
    location = StringField('Localização no Depósito', validators=[Optional(), Length(max=100)])
    price = DecimalField('Preço Unitário (R$)', validators=[Optional()], places=2)
    supplier_id = SelectField('Fornecedor', validators=[Optional()], coerce=lambda x: int(x) if x else None)
    expiration_date = StringField('Data de Validade', validators=[Optional()])
    ca_number = StringField('Número do CA (para EPIs)', validators=[Optional(), Length(max=50)])
    image = FileField('Imagem do Item', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens são permitidas!')
    ])
    
    def __init__(self, *args, **kwargs):
        super(StockItemForm, self).__init__(*args, **kwargs)
        self.supplier_id.choices = [(0, 'Selecione um fornecedor (opcional)')] + [
            (s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()
        ]
        
class StockMovementForm(FlaskForm):
    """Formulário para movimentação de estoque"""
    stock_item_id = SelectField('Item', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantidade', validators=[DataRequired(), NumberRange(min=1)], default=1)
    direction = SelectField('Tipo de Movimentação', choices=[
        ('entrada', 'Entrada em Estoque'),
        ('saida', 'Saída de Estoque')
    ], validators=[DataRequired()])
    description = TextAreaField('Motivo/Descrição', validators=[DataRequired()])
    reference = StringField('Referência (Funcionário, OS, etc)', validators=[Optional(), Length(max=100)])
    service_order_id = SelectField('Ordem de Serviço', validators=[Optional()], coerce=lambda x: int(x) if x else None)
    
    def __init__(self, *args, **kwargs):
        super(StockMovementForm, self).__init__(*args, **kwargs)
        self.stock_item_id.choices = [(i.id, f"{i.name} - {i.quantity} em estoque") 
                                      for i in StockItem.query.order_by(StockItem.name).all()]
        
        # Ordens de serviço abertas
        self.service_order_id.choices = [(0, 'Nenhuma OS relacionada')] + [
            (s.id, f"OS #{s.id} - {s.client.name}") 
            for s in ServiceOrder.query.filter(ServiceOrder.status != ServiceOrderStatus.fechada).order_by(ServiceOrder.id.desc()).all()
        ]

        
class VehicleMaintenanceForm(FlaskForm):
    vehicle_id = SelectField('Veículo', validators=[DataRequired()], coerce=int)
    date = StringField('Data da Manutenção', validators=[DataRequired()], render_kw={"type": "date"})
    mileage = IntegerField('Hodômetro/Horímetro', validators=[Optional()])
    description = TextAreaField('Descrição do Serviço', validators=[DataRequired(), Length(max=1000)])
    cost = DecimalField('Custo (R$)', validators=[Optional()], places=2)
    service_provider = StringField('Prestador de Serviço', validators=[Optional(), Length(max=100)])
    invoice_number = StringField('Número da Nota Fiscal', validators=[Optional(), Length(max=50)])
    performed_by_id = SelectField('Realizado por', validators=[Optional()], coerce=lambda x: int(x) if x else None)
    
    def __init__(self, *args, **kwargs):
        super(VehicleMaintenanceForm, self).__init__(*args, **kwargs)
        # Lista de veículos
        self.vehicle_id.choices = [(v.id, f"{v.identifier} ({v.brand} {v.model})") 
                                    for v in Vehicle.query.order_by(Vehicle.identifier).all()]
        
        # Lista de funcionários
        self.performed_by_id.choices = [(0, 'Serviço Externo')] + [
            (u.id, f"{u.name}") 
            for u in User.query.filter_by(active=True).order_by(User.name).all()
        ]
