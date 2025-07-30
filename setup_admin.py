"""
Script simples para criar usuário administrador no SAMAPE
Execute este arquivo para garantir que existe um admin no sistema
"""

print("🚀 Iniciando criação de usuário administrador...")

# Configurar variáveis de ambiente básicas
import os
os.environ['FLASK_ENV'] = 'development'
os.environ['SECRET_KEY'] = 'samape-dev-key-2024'
os.environ['DATABASE_URL'] = 'sqlite:///samape.db'

try:
    print("📦 Importando módulos...")
    from app import app, db
    from models import User, UserRole
    
    print("🔧 Configurando aplicação...")
    with app.app_context():
        print("🗄️ Criando tabelas...")
        db.create_all()
        
        print("👤 Verificando usuários existentes...")
        
        # Tentar diferentes usernames
        admin_candidates = ['admin', 'Alessandro_jr', 'samape_admin', 'root']
        
        existing_admin = None
        for username in admin_candidates:
            user = User.query.filter_by(username=username).first()
            if user and user.role == UserRole.admin:
                existing_admin = user
                break
        
        if existing_admin:
            print(f"✅ Usuário administrador encontrado: {existing_admin.username}")
            print(f"📧 Email: {existing_admin.email}")
            username = existing_admin.username
            password = "admin123"  # Senha padrão (pode ter sido alterada)
        else:
            print("🆕 Criando novo usuário administrador...")
            
            # Criar admin com credenciais simples
            username = "admin"
            password = "admin123"
            
            # Verificar se username já existe (não admin)
            if User.query.filter_by(username=username).first():
                username = "samape_admin"
            
            admin = User(
                username=username,
                name="Administrador Sistema",
                email="admin@samape.local",
                role=UserRole.admin,
                active=True
            )
            
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            
            print(f"✅ Usuário criado com sucesso!")
        
        print("\n" + "="*50)
        print("🎉 CREDENCIAIS DE ACESSO AO SAMAPE:")
        print(f"   🔑 Usuário: {username}")
        print(f"   🔒 Senha: {password}")
        print("="*50)
        print("📱 Para acessar:")
        print("   1. Execute a aplicação (python app.py)")
        print("   2. Acesse http://localhost:5000")
        print("   3. Clique em 'Login' ou vá para /login")
        print("   4. Use as credenciais acima")
        print("="*50)
        print("⚠️  IMPORTANTE:")
        print("   - Altere a senha após o primeiro login")
        print("   - Estas são credenciais de desenvolvimento")
        print("   - Em produção, use credenciais mais seguras")
        print("="*50)

except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print("💡 Certifique-se de que:")
    print("   - Está no diretório correto")
    print("   - O ambiente virtual está ativo")
    print("   - As dependências estão instaladas")

except Exception as e:
    print(f"❌ Erro: {e}")
    print("💡 Verifique se o banco de dados está acessível")

print("\n🏁 Script finalizado!")
