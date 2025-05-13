import os
import logging
from datetime import timedelta

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from jinja_filters import nl2br, format_document, format_currency, status_color, absolute_value


# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create SQLAlchemy base class
class Base(DeclarativeBase):
    pass


# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()

# Create application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "development_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://postgres:qUngJAyBvLWQdkmSkZEjjEoMoDVzOBnx@trolley.proxy.rlwy.net:22285/railway")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure session
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=24)  # Aumentando para 24 horas
app.config["SESSION_COOKIE_SECURE"] = False  # Desativado em ambiente de desenvolvimento
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = None  # Desativando SameSite para corrigir problemas de sessão

# Configure CSRF protection (temporariamente desabilitado para resolver problemas)
app.config["WTF_CSRF_ENABLED"] = False 
app.config["WTF_CSRF_TIME_LIMIT"] = 3600  # 1 hour
app.config["WTF_CSRF_SSL_STRICT"] = False  # Para ambiente de desenvolvimento

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)

# Adicionar exceção CSRF para as rotas de exclusão de cliente
csrf.init_app(app)
csrf.exempt('/clientes/<int:id>/excluir')
csrf.exempt('/admin/clientes/<int:id>/excluir-direto')

# Configure login manager
login_manager.login_view = "login"
login_manager.login_message = "Por favor, faça login para acessar esta página."
login_manager.login_message_category = "warning"

# Import models and create tables
with app.app_context():
    import models
    from models import User
    db.create_all()
    
    # Setup user loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

# Register Jinja filters
app.jinja_env.filters['nl2br'] = nl2br
app.jinja_env.filters['format_document'] = format_document
app.jinja_env.filters['format_currency'] = format_currency
app.jinja_env.filters['status_color'] = status_color
app.jinja_env.filters['abs'] = absolute_value

# Import and register routes
from routes import register_routes
register_routes(app)

# Import vehicle routes
import routes_vehicles

# Registrar as rotas específicas de controle de frota manualmente
app.add_url_rule('/vehicles', view_func=routes_vehicles.vehicles, methods=['GET'])
app.add_url_rule('/add_vehicle', view_func=routes_vehicles.add_vehicle, methods=['GET', 'POST'])
app.add_url_rule('/view_vehicle/<int:vehicle_id>', view_func=routes_vehicles.view_vehicle, methods=['GET'])
app.add_url_rule('/edit_vehicle/<int:vehicle_id>', view_func=routes_vehicles.edit_vehicle, methods=['GET', 'POST'])
app.add_url_rule('/delete_vehicle/<int:vehicle_id>', view_func=routes_vehicles.delete_vehicle, methods=['GET', 'POST'])
app.add_url_rule('/delete_vehicle_image/<int:vehicle_id>', view_func=routes_vehicles.delete_vehicle_image, methods=['GET', 'POST'])

app.add_url_rule('/refuelings', view_func=routes_vehicles.refuelings, methods=['GET'])
app.add_url_rule('/add_refueling', view_func=routes_vehicles.add_refueling, methods=['GET', 'POST'])
app.add_url_rule('/view_refueling/<int:refueling_id>', view_func=routes_vehicles.view_refueling, methods=['GET'])
app.add_url_rule('/edit_refueling/<int:refueling_id>', view_func=routes_vehicles.edit_refueling, methods=['GET', 'POST'])
app.add_url_rule('/delete_refueling/<int:refueling_id>', view_func=routes_vehicles.delete_refueling, methods=['GET', 'POST'])
app.add_url_rule('/delete_refueling_receipt/<int:refueling_id>', view_func=routes_vehicles.delete_refueling_receipt, methods=['GET', 'POST'])

app.add_url_rule('/maintenances', view_func=routes_vehicles.maintenances, methods=['GET'])
app.add_url_rule('/add_maintenance', view_func=routes_vehicles.add_maintenance, methods=['GET', 'POST'])
app.add_url_rule('/view_maintenance/<int:maintenance_id>', view_func=routes_vehicles.view_maintenance, methods=['GET'])
app.add_url_rule('/edit_maintenance/<int:maintenance_id>', view_func=routes_vehicles.edit_maintenance, methods=['GET', 'POST'])
app.add_url_rule('/delete_maintenance/<int:maintenance_id>', view_func=routes_vehicles.delete_maintenance, methods=['GET', 'POST'])
app.add_url_rule('/delete_maintenance_invoice/<int:maintenance_id>', view_func=routes_vehicles.delete_maintenance_invoice, methods=['GET', 'POST'])

app.add_url_rule('/travel_logs', view_func=routes_vehicles.travel_logs, methods=['GET'])
app.add_url_rule('/add_travel_log', view_func=routes_vehicles.add_travel_log, methods=['GET', 'POST'])
app.add_url_rule('/view_travel_log/<int:travel_log_id>', view_func=routes_vehicles.view_travel_log, methods=['GET'])
app.add_url_rule('/edit_travel_log/<int:travel_log_id>', view_func=routes_vehicles.edit_travel_log, methods=['GET', 'POST'])
app.add_url_rule('/complete_travel_log/<int:travel_log_id>', view_func=routes_vehicles.complete_travel_log, methods=['GET', 'POST'])
app.add_url_rule('/cancel_travel_log/<int:travel_log_id>', view_func=routes_vehicles.cancel_travel_log, methods=['GET', 'POST'])
app.add_url_rule('/delete_travel_log/<int:travel_log_id>', view_func=routes_vehicles.delete_travel_log, methods=['GET', 'POST'])

# Create initial admin user if needed
with app.app_context():
    # Certificando que temos pelo menos um usuário admin no sistema
    from models import User, UserRole

    # Verificar se já existe um usuário admin
    if User.query.filter_by(role=UserRole.admin).count() == 0:
        try:
            admin = User(
                username="admin",
                name="Administrador",
                email="admin@samape.com",
                role=UserRole.admin,
                active=True
            )
            admin.set_password("admin123")
            
            db.session.add(admin)
            db.session.commit()
            
            print("Usuário administrador criado com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao criar usuário administrador: {e}")
