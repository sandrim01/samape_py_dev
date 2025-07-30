#!/usr/bin/env python3
"""
Script para criar usuário administrador padrão no SAMAPE
"""

import os
import sys

# Adicionar o diretório atual ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_admin_user():
    """Cria o usuário administrador padrão"""
    try:
        from app import app
        from database import db
        from models import User, UserRole
        
        with app.app_context():
            print("🔧 Criando tabelas do banco de dados...")
            db.create_all()
            
            # Verificar se já existe algum usuário admin
            admin_user = User.query.filter_by(role=UserRole.admin).first()
            
            if admin_user:
                print(f"✅ Usuário administrador já existe: {admin_user.username}")
                print(f"📧 Email: {admin_user.email}")
                print("💡 Use as credenciais existentes ou redefina a senha.")
                return admin_user.username, "Senha existente"
            
            # Criar novo usuário admin
            print("👤 Criando novo usuário administrador...")
            
            # Credenciais padrão
            username = "admin"
            password = "admin123"
            email = "admin@samape.com"
            name = "Administrador"
            
            # Verificar se username já existe
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                username = "samape_admin"
            
            # Criar o usuário
            admin = User(
                username=username,
                name=name,
                email=email,
                role=UserRole.admin,
                active=True
            )
            
            # Definir senha
            admin.set_password(password)
            
            # Salvar no banco
            db.session.add(admin)
            db.session.commit()
            
            print(f"✅ Usuário administrador criado com sucesso!")
            print(f"👤 Usuário: {username}")
            print(f"🔑 Senha: {password}")
            print(f"📧 Email: {email}")
            print(f"🛡️  Tipo: Administrador")
            
            return username, password
            
    except Exception as e:
        print(f"❌ Erro ao criar usuário administrador: {e}")
        return None, None

def create_alternative_admin():
    """Cria um admin alternativo com credenciais simples"""
    try:
        from app import app
        from database import db
        from models import User, UserRole
        
        with app.app_context():
            username = "root"
            password = "123456"
            email = "root@samape.local"
            name = "Root Administrator"
            
            # Verificar se já existe
            existing = User.query.filter_by(username=username).first()
            if existing:
                print(f"✅ Usuário {username} já existe")
                return username, password
            
            # Criar usuário root
            root_user = User(
                username=username,
                name=name,
                email=email,
                role=UserRole.admin,
                active=True
            )
            
            root_user.set_password(password)
            db.session.add(root_user)
            db.session.commit()
            
            print(f"✅ Usuário root criado!")
            return username, password
            
    except Exception as e:
        print(f"❌ Erro ao criar usuário root: {e}")
        return None, None

def main():
    print("🚀 SAMAPE - Criação de Usuário Administrador")
    print("=" * 50)
    
    # Tentar criar admin padrão
    username, password = create_admin_user()
    
    if not username:
        print("\n🔄 Tentando criar usuário alternativo...")
        username, password = create_alternative_admin()
    
    if username and password:
        print("\n" + "=" * 50)
        print("🎉 CREDENCIAIS DE ACESSO:")
        print(f"   Usuário: {username}")
        print(f"   Senha: {password}")
        print("=" * 50)
        print("⚠️  IMPORTANTE:")
        print("   1. Altere a senha após o primeiro login")
        print("   2. Use estas credenciais para acessar o sistema")
        print("   3. Acesse via /login na aplicação")
        print("=" * 50)
        return 0
    else:
        print("\n❌ Não foi possível criar usuário administrador")
        print("💡 Verifique se:")
        print("   - O banco de dados está configurado")
        print("   - As dependências estão instaladas")
        print("   - Não há erros de sintaxe nos modelos")
        return 1

if __name__ == "__main__":
    sys.exit(main())
