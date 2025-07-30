#!/usr/bin/env python3
"""
Script de diagnóstico para problemas do SAMAPE no Railway
"""

import os
import sys

def check_environment_variables():
    """Verifica se todas as variáveis de ambiente necessárias estão definidas"""
    print("🔍 Verificando variáveis de ambiente...")
    
    required_vars = [
        'SESSION_SECRET',
        'DATABASE_URL',
        'FLASK_ENV'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: NÃO DEFINIDA")
        else:
            # Mostrar apenas os primeiros e últimos caracteres para segurança
            if len(value) > 10:
                masked_value = value[:4] + "***" + value[-4:]
            else:
                masked_value = "***"
            print(f"✅ {var}: {masked_value}")
    
    return missing_vars

def check_database_connection():
    """Testa a conexão com o banco de dados"""
    print("\n🗄️  Testando conexão com banco...")
    
    try:
        # Configurar variáveis de ambiente mínimas se não existirem
        if not os.environ.get('SESSION_SECRET'):
            os.environ['SESSION_SECRET'] = 'temp-secret-for-testing'
        if not os.environ.get('FLASK_ENV'):
            os.environ['FLASK_ENV'] = 'production'
            
        from app import app, db
        
        with app.app_context():
            # Tentar executar uma query simples
            result = db.engine.execute("SELECT 1").scalar()
            if result == 1:
                print("✅ Conexão com banco funcionando")
                return True
            else:
                print("❌ Problema na conexão com banco")
                return False
                
    except Exception as e:
        print(f"❌ Erro na conexão com banco: {e}")
        return False

def check_database_schema():
    """Verifica se as tabelas existem no banco"""
    print("\n📋 Verificando esquema do banco...")
    
    try:
        from app import app, db
        from sqlalchemy import inspect
        
        with app.app_context():
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = [
                'user', 'client', 'equipment', 'service_order', 
                'financial_entry', 'action_log'
            ]
            
            missing_tables = []
            for table in expected_tables:
                if table in tables:
                    print(f"✅ Tabela '{table}' existe")
                else:
                    missing_tables.append(table)
                    print(f"❌ Tabela '{table}' não encontrada")
            
            return missing_tables
            
    except Exception as e:
        print(f"❌ Erro ao verificar esquema: {e}")
        return ['erro_de_conexao']

def check_admin_user():
    """Verifica se existe usuário administrador"""
    print("\n👤 Verificando usuário administrador...")
    
    try:
        from app import app, db
        from models import User, UserRole
        
        with app.app_context():
            admin_users = User.query.filter_by(role=UserRole.admin).all()
            
            if admin_users:
                print(f"✅ {len(admin_users)} usuário(s) administrador(es) encontrado(s):")
                for user in admin_users:
                    print(f"   - {user.username} ({user.email})")
                return True
            else:
                print("❌ Nenhum usuário administrador encontrado")
                return False
                
    except Exception as e:
        print(f"❌ Erro ao verificar usuários: {e}")
        return False

def check_import_issues():
    """Verifica problemas de importação"""
    print("\n📦 Verificando imports...")
    
    try:
        import flask
        print(f"✅ Flask {flask.__version__}")
    except ImportError as e:
        print(f"❌ Flask: {e}")
        return False
    
    try:
        import sqlalchemy
        print(f"✅ SQLAlchemy {sqlalchemy.__version__}")
    except ImportError as e:
        print(f"❌ SQLAlchemy: {e}")
        return False
    
    try:
        import psycopg2
        print("✅ psycopg2 (PostgreSQL)")
    except ImportError as e:
        print(f"⚠️  psycopg2: {e} (pode ser normal se usando SQLite)")
    
    try:
        from app import app
        print("✅ app.py importado com sucesso")
        return True
    except Exception as e:
        print(f"❌ Erro ao importar app.py: {e}")
        return False

def generate_railway_config():
    """Gera arquivo de configuração para Railway"""
    print("\n🚂 Gerando configuração para Railway...")
    
    railway_config = """# Railway Configuration for SAMAPE

# Variáveis de ambiente obrigatórias:
SESSION_SECRET=<sua-chave-secreta-aqui>
DATABASE_URL=<url-do-banco-postgresql>
FLASK_ENV=production

# Configurações opcionais:
PORT=5000
ADMIN_DEFAULT_PASSWORD=admin123

# Comando de start:
python app.py

# Procfile (se necessário):
web: python app.py

# Comando de build (se necessário):
pip install -r requirements.txt
"""
    
    try:
        with open('railway_config.txt', 'w') as f:
            f.write(railway_config)
        print("✅ Arquivo railway_config.txt criado")
    except Exception as e:
        print(f"❌ Erro ao criar arquivo: {e}")

def fix_common_issues():
    """Sugere correções para problemas comuns"""
    print("\n🔧 Sugestões de correção:")
    
    print("1. 📍 No Railway, configure as variáveis de ambiente:")
    print("   - SESSION_SECRET: chave aleatória de 32+ caracteres")
    print("   - DATABASE_URL: URL do PostgreSQL fornecida pelo Railway")
    print("   - FLASK_ENV: production")
    
    print("\n2. 🗄️  Para problemas de banco:")
    print("   - Execute 'python migrate_db.py' localmente")
    print("   - Verifique se as migrações foram aplicadas")
    print("   - Confirme se o PostgreSQL está ativo no Railway")
    
    print("\n3. 📦 Para problemas de dependências:")
    print("   - Verifique se requirements.txt está atualizado")
    print("   - Execute 'pip freeze > requirements.txt'")
    print("   - Confirme se todas as dependências estão listadas")
    
    print("\n4. 🚀 Para problemas de deploy:")
    print("   - Verifique se o PORT está configurado corretamente")
    print("   - Confirme se app.run() usa host='0.0.0.0'")
    print("   - Verifique logs do Railway para erros específicos")

def main():
    print("🔍 SAMAPE - Diagnóstico de Problemas Railway")
    print("=" * 60)
    
    # Verificações
    missing_vars = check_environment_variables()
    db_connected = check_database_connection()
    missing_tables = check_database_schema() if db_connected else ['conexao_falhou']
    admin_exists = check_admin_user() if db_connected else False
    imports_ok = check_import_issues()
    
    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DO DIAGNÓSTICO:")
    print(f"   Variáveis de ambiente: {'✅' if not missing_vars else '❌'}")
    print(f"   Conexão com banco: {'✅' if db_connected else '❌'}")
    print(f"   Esquema do banco: {'✅' if not missing_tables else '❌'}")
    print(f"   Usuário admin: {'✅' if admin_exists else '❌'}")
    print(f"   Imports: {'✅' if imports_ok else '❌'}")
    
    # Gerar arquivo de configuração
    generate_railway_config()
    
    # Sugestões
    fix_common_issues()
    
    print("\n" + "=" * 60)
    if not missing_vars and db_connected and not missing_tables and admin_exists and imports_ok:
        print("🎉 Tudo parece estar funcionando!")
    else:
        print("⚠️  Problemas encontrados - verifique as sugestões acima")

if __name__ == "__main__":
    main()
