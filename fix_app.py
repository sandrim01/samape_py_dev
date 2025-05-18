#!/usr/bin/env python3
import os
import sys

# Restaurar backup do main.py se existir
if os.path.exists('main.py.bak'):
    os.rename('main.py.bak', 'main.py')
    print("Arquivo main.py restaurado do backup")

# Restaurar app.py original com as configurações corretas
app_content = """import os
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
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=1)
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

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

# Create initial admin user if needed
with app.app_context():
    if hasattr(app, 'create_initial_admin'):
        app.create_initial_admin()
"""

with open('app.py', 'w') as f:
    f.write(app_content)
    print("Arquivo app.py restaurado")

# Criar versão simplificada do template de login
login_template = """<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - SAMAPE</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <style>
        body {
            background: linear-gradient(135deg, #0d6efd 0%, #084298 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 0;
        }
        .login-container {
            width: 100%;
            max-width: 400px;
            padding: 15px;
        }
        .login-card {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
        }
        .card-header {
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            padding: 15px 0;
        }
        .login-logo {
            text-align: center;
        }
        .login-title {
            font-size: 1.5rem;
            text-align: center;
            margin-bottom: 20px;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-card card">
            <div class="card-header">
                <div class="login-logo">
                    <h2>SAMAPE</h2>
                </div>
            </div>
            <div class="card-body p-4">
                <h3 class="login-title">Acesso ao Sistema</h3>
                
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                                {{ message }}
                                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                            </div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                <form method="post" novalidate>
                    {{ form.hidden_tag() }}
                    
                    <div class="mb-4">
                        <label for="username" class="form-label">{{ form.username.label }}</label>
                        {{ form.username(class="form-control", id="username", placeholder="Digite seu usuário", autocomplete="username") }}
                        {% if form.username.errors %}
                            <div class="invalid-feedback d-block">
                                {% for error in form.username.errors %}
                                    {{ error }}
                                {% endfor %}
                            </div>
                        {% endif %}
                    </div>
                    
                    <div class="mb-4">
                        <label for="password" class="form-label">{{ form.password.label }}</label>
                        {{ form.password(class="form-control", id="password", placeholder="Digite sua senha", autocomplete="current-password") }}
                        {% if form.password.errors %}
                            <div class="invalid-feedback d-block">
                                {% for error in form.password.errors %}
                                    {{ error }}
                                {% endfor %}
                            </div>
                        {% endif %}
                    </div>
                    
                    <div class="mb-4 form-check">
                        {{ form.remember_me(class="form-check-input", id="remember_me") }}
                        <label class="form-check-label" for="remember_me">{{ form.remember_me.label }}</label>
                    </div>
                    
                    <div class="d-grid gap-2">
                        <button type="submit" class="btn btn-primary btn-lg">
                            <i class="fas fa-sign-in-alt me-2"></i>Entrar
                        </button>
                    </div>
                </form>
            </div>
        </div>
        
        <div class="text-center mt-4 text-white">
            <small>&copy; 2025 SAMAPE - Sistema de Gestão de Serviços</small>
        </div>
    </div>
    
    <!-- Bootstrap Bundle with Popper -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Salvar o template de login
os.makedirs('templates', exist_ok=True)
with open('templates/login_standalone.html', 'w') as f:
    f.write(login_template)
    print("Template de login criado")

print("Configuração da aplicação restaurada e corrigida")
