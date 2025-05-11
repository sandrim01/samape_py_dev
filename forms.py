from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, DecimalField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
import re
from models import User, Client, ServiceOrderStatus, UserRole, FinancialEntryType

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
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
    type = StringField('Tipo', validators=[DataRequired(), Length(max=50)])
    brand = StringField('Marca', validators=[Optional(), Length(max=50)])
    model = StringField('Modelo', validators=[Optional(), Length(max=50)])
    serial_number = StringField('Número de Série', validators=[Optional(), Length(max=50)])
    year = StringField('Ano', validators=[Optional(), Length(max=4)])

class ServiceOrderForm(FlaskForm):
    client_id = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    equipment_ids = HiddenField('Equipamentos', validators=[Optional()])
    responsible_id = SelectField('Responsável', coerce=int, validators=[Optional()])
    description = TextAreaField('Descrição do Serviço', validators=[DataRequired()])
    estimated_value = DecimalField('Valor Estimado (R$)', validators=[Optional()], places=2)
    status = SelectField('Status', choices=[(status.name, status.value) for status in ServiceOrderStatus], validators=[DataRequired()])

class CloseServiceOrderForm(FlaskForm):
    invoice_number = StringField('Número da NF-e', validators=[DataRequired()])
    original_amount = DecimalField('Valor Original (R$)', validators=[DataRequired()], places=2)
    discount_amount = DecimalField('Valor do Desconto (R$)', validators=[Optional()], places=2)
    invoice_amount = DecimalField('Valor Final com Desconto (R$)', validators=[DataRequired()], places=2)
    service_details = TextAreaField('Detalhes do Serviço Executado', validators=[DataRequired()])

class FinancialEntryForm(FlaskForm):
    service_order_id = SelectField('Ordem de Serviço', coerce=int, validators=[Optional()])
    description = StringField('Descrição', validators=[DataRequired(), Length(max=200)])
    amount = DecimalField('Valor (R$)', validators=[DataRequired()], places=2)
    type = SelectField('Tipo', choices=[(t.name, t.value) for t in FinancialEntryType], validators=[DataRequired()])
    date = StringField('Data', validators=[DataRequired()])

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
