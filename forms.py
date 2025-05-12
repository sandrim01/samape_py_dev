from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, DecimalField, HiddenField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError, NumberRange
import re
from models import User, Client, ServiceOrderStatus, UserRole, FinancialEntryType, Supplier, Part, OrderStatus

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
        Length(min=8, message='A senha deve ter pelo menos 8 caracteres')
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
        
        # Obter marcas distintas
        brands = db.session.query(distinct(Equipment.brand)).order_by(Equipment.brand).all()
        self.brand_select.choices = [('', 'Selecione uma marca')] + [(b[0], b[0]) for b in brands if b[0]]
        
        # Obter tipos distintos
        types = db.session.query(distinct(Equipment.type)).order_by(Equipment.type).all()
        self.type_select.choices = [('', 'Selecione um tipo')] + [(t[0], t[0]) for t in types if t[0]]
        
        # Modelo será preenchido via AJAX com base na marca selecionada

class ServiceOrderForm(FlaskForm):
    client_id = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    equipment_ids = HiddenField('Equipamentos', validators=[Optional()])
    responsible_id = SelectField('Responsável', coerce=int, validators=[Optional()])
    description = TextAreaField('Descrição do Serviço', validators=[DataRequired()])
    estimated_value = DecimalField('Valor Estimado (R$)', validators=[Optional()], places=2)
    status = SelectField('Status', choices=[(status.name, status.value) for status in ServiceOrderStatus], validators=[DataRequired()])
    images = FileField('Imagens do Equipamento', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Apenas imagens são permitidas!')
    ], render_kw={"multiple": True})
    image_descriptions = TextAreaField('Descrições das Imagens (separadas por ponto e vírgula)', validators=[Optional()])

class CloseServiceOrderForm(FlaskForm):
    invoice_number = StringField('Número da NF-e', validators=[DataRequired()])
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
    part_id = SelectField('Peça', validators=[Optional()], coerce=lambda x: int(x) if x else None)
    description = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    quantity = IntegerField('Quantidade', validators=[DataRequired(), NumberRange(min=1)], default=1)
    unit_price = DecimalField('Preço Unitário (R$)', validators=[Optional()], places=2)
    total_price = DecimalField('Preço Total (R$)', validators=[Optional()], places=2)
    status = SelectField('Status', choices=[(status.name, status.value) for status in OrderStatus], validators=[DataRequired()])
    notes = TextAreaField('Observações', validators=[Optional()])
    id = HiddenField()

    def __init__(self, *args, **kwargs):
        super(OrderItemForm, self).__init__(*args, **kwargs)
        # Peças para o dropdown
        from models import Part
        self.part_id.choices = [('', 'Selecione uma peça ou digite a descrição')] + [
            (p.id, f"{p.name} - {p.part_number or 'S/N'}") 
            for p in Part.query.order_by(Part.name).all()
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
