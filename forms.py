from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SelectField, DecimalField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
import re
from models import User, Client, ServiceOrderStatus, UserRole, FinancialEntryType

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
    equipment_ids = SelectField('Equipamentos', validators=[Optional()], render_kw={"multiple": True})
    responsible_id = SelectField('Responsável', coerce=int, validators=[Optional()])
    description = TextAreaField('Descrição do Serviço', validators=[DataRequired()])
    status = SelectField('Status', choices=[(status.name, status.value) for status in ServiceOrderStatus], validators=[DataRequired()])

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
