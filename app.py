import os
import logging
from datetime import timedelta

from flask import Flask
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from database import db, init_db
from jinja_filters import nl2br, format_document, format_currency, status_color, absolute_value
from logging_config import setup_logging
from config import config

# Create application
app = Flask(__name__)

# Load configuration
config_name = os.environ.get('FLASK_ENV', 'development')
app.config.from_object(config[config_name])

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Setup logging
setup_logging(app)

# Initialize extensions
login_manager = LoginManager()
csrf = CSRFProtect()

# Initialize extensions with app
init_db(app)
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

# Create initial admin user if needed
with app.app_context():
    if hasattr(app, 'create_initial_admin'):
        app.create_initial_admin()
    else:
        # Fallback: criar admin diretamente se não houver função
        from models import User, UserRole
        try:
            # Verificar se existe algum admin
            admin_exists = User.query.filter_by(role=UserRole.admin).first()
            if not admin_exists:
                # Criar admin padrão
                admin = User(
                    username='admin',
                    name='Administrador',
                    email='admin@samape.com',
                    role=UserRole.admin,
                    active=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                app.logger.info("Admin user created: username=admin, password=admin123")
        except Exception as e:
            app.logger.error(f"Error creating admin user: {e}")

if __name__ == '__main__':
    # Configuração para Railway (produção)
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') != 'production'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
