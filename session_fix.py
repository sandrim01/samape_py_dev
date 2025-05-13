"""
Script para corrigir problemas de sessão/login no sistema
"""
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def reset_admin_password():
    """Reseta a senha do usuário admin para garantir que funcione"""
    with app.app_context():
        admin = User.query.filter_by(username="admin").first()
        if admin:
            admin.password_hash = generate_password_hash("admin123")
            db.session.commit()
            print("Senha do usuário admin resetada com sucesso!")

if __name__ == "__main__":
    reset_admin_password()