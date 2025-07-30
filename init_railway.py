#!/usr/bin/env python3
"""
Script para inicializar o banco de dados no Railway
"""

import os
import sys

def setup_environment():
    """Configura variáveis de ambiente básicas se não estiverem definidas"""
    if not os.environ.get('SESSION_SECRET'):
        # Gerar uma chave temporária se não existir
        import secrets
        os.environ['SESSION_SECRET'] = secrets.token_hex(32)
        print("⚠️  SESSION_SECRET temporária gerada")
    
    if not os.environ.get('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'production'

def initialize_database():
    """Inicializa o banco de dados"""
    print("🗄️  Inicializando banco de dados...")
    
    try:
        setup_environment()
        
        from app import app, db
        from models import User, UserRole
        
        with app.app_context():
            # Criar todas as tabelas
            print("📋 Criando tabelas...")
            db.create_all()
            
            # Verificar se existe admin
            admin_user = User.query.filter_by(role=UserRole.admin).first()
            
            if not admin_user:
                print("👤 Criando usuário administrador...")
                admin = User(
                    username='admin',
                    name='Administrador SAMAPE',
                    email='admin@samape.com',
                    role=UserRole.admin,
                    active=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
                print("✅ Usuário admin criado: username=admin, password=admin123")
            else:
                print("✅ Usuário administrador já existe")
                
            print("✅ Banco de dados inicializado com sucesso!")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao inicializar banco: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 SAMAPE - Inicialização Railway")
    print("=" * 50)
    
    if initialize_database():
        print("\n🎉 Inicialização concluída com sucesso!")
        print("\n📋 Credenciais de acesso:")
        print("   URL: https://samape-py-samapedev.up.railway.app/")
        print("   Usuário: admin")
        print("   Senha: admin123")
    else:
        print("\n💥 Falha na inicialização!")
        sys.exit(1)

if __name__ == "__main__":
    main()
