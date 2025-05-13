"""
Script para resetar completamente o sistema de autenticação
"""
from app import app, db
from models import User, UserRole
from werkzeug.security import generate_password_hash
import os

def reset_authentication():
    """Reseta completamente o sistema de autenticação"""
    with app.app_context():
        try:
            # 1. Recuperar todos os usuários administradores
            admins = User.query.filter_by(role=UserRole.admin).all()
            
            # 2. Imprimir informações sobre os administradores encontrados
            print(f"Encontrados {len(admins)} usuários administradores:")
            for admin in admins:
                print(f"- ID: {admin.id}, Username: {admin.username}, Email: {admin.email}")
            
            # 3. Redefinir a senha de todos os administradores para garantir
            for admin in admins:
                admin.password_hash = generate_password_hash("admin123")
                print(f"Senha resetada para o usuário {admin.username}")
            
            # Se não houver administradores, criar um novo
            if len(admins) == 0:
                print("Nenhum administrador encontrado. Criando um novo...")
                new_admin = User(
                    username="admin",
                    name="Administrador",
                    email="admin@samape.com",
                    role=UserRole.admin,
                    active=True
                )
                new_admin.set_password("admin123")
                db.session.add(new_admin)
                print("Novo administrador criado com sucesso!")
            
            # 4. Commit das alterações
            db.session.commit()
            print("Alterações salvas com sucesso!")
        
        except Exception as e:
            db.session.rollback()
            print(f"Erro durante o reset de autenticação: {e}")

if __name__ == "__main__":
    reset_authentication()