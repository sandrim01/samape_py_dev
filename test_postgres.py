#!/usr/bin/env python3
"""
Teste específico de conexão PostgreSQL Railway
"""

import os
import sys

def test_database_connection():
    """Testa a conexão com o banco PostgreSQL"""
    
    # URL fornecida pelo usuário
    database_url = "postgresql://postgres:fzsZiDkvLIsSlVGzrOyEbgWTStUvfsQA@centerbeam.proxy.rlwy.net:51097/railway"
    
    print("🗄️  Testando conexão PostgreSQL Railway...")
    print(f"URL: {database_url[:30]}...{database_url[-20:]}")
    
    try:
        # Tentar com psycopg2
        import psycopg2
        print("✅ psycopg2 importado")
        
        # Tentar conexão direta
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Teste simples
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ PostgreSQL conectado: {version[0][:50]}...")
        
        # Testar criação de tabela
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50)
            );
        """)
        conn.commit()
        print("✅ Criação de tabela funcionando")
        
        # Limpeza
        cursor.execute("DROP TABLE IF EXISTS test_table;")
        conn.commit()
        
        cursor.close()
        conn.close()
        print("✅ Banco PostgreSQL funcionando perfeitamente!")
        return True
        
    except ImportError:
        print("❌ psycopg2 não instalado")
        return False
        
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False

def test_sqlalchemy_connection():
    """Testa conexão via SQLAlchemy"""
    
    database_url = "postgresql://postgres:fzsZiDkvLIsSlVGzrOyEbgWTStUvfsQA@centerbeam.proxy.rlwy.net:51097/railway"
    
    print("\n🔗 Testando SQLAlchemy...")
    
    try:
        from sqlalchemy import create_engine, text
        
        # Criar engine
        engine = create_engine(database_url)
        print("✅ SQLAlchemy engine criado")
        
        # Testar conexão
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            if result.scalar() == 1:
                print("✅ SQLAlchemy conectado com sucesso")
                return True
                
    except Exception as e:
        print(f"❌ Erro SQLAlchemy: {e}")
        return False

def main():
    print("🔍 DIAGNÓSTICO POSTGRESQL RAILWAY")
    print("=" * 50)
    
    # Definir variável de ambiente
    os.environ['DATABASE_URL'] = "postgresql://postgres:fzsZiDkvLIsSlVGzrOyEbgWTStUvfsQA@centerbeam.proxy.rlwy.net:51097/railway"
    
    # Testes
    pg_ok = test_database_connection()
    sqlalchemy_ok = test_sqlalchemy_connection()
    
    print("\n" + "=" * 50)
    print("📊 RESULTADO:")
    print(f"   PostgreSQL direto: {'✅' if pg_ok else '❌'}")
    print(f"   SQLAlchemy: {'✅' if sqlalchemy_ok else '❌'}")
    
    if pg_ok and sqlalchemy_ok:
        print("\n🎉 Banco funcionando! Problema deve ser na aplicação.")
        print("\n🔧 Próximos passos:")
        print("1. Configurar DATABASE_URL no Railway")
        print("2. Voltar para app.py completo")
        print("3. Testar aplicação")
    else:
        print("\n💥 Problema no banco identificado!")
        print("Verifique se PostgreSQL está ativo no Railway")
        
    return 0 if (pg_ok and sqlalchemy_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
