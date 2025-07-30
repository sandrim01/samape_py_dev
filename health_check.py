#!/usr/bin/env python3
"""
Health check simples para Railway
"""

import os
import sys

def main():
    print("🏥 SAMAPE Health Check")
    print("=" * 30)
    
    # Verificar variáveis básicas
    port = os.environ.get('PORT', '5000')
    flask_env = os.environ.get('FLASK_ENV', 'development')
    session_secret = os.environ.get('SESSION_SECRET', 'NOT_SET')
    database_url = os.environ.get('DATABASE_URL', 'NOT_SET')
    
    print(f"PORT: {port}")
    print(f"FLASK_ENV: {flask_env}")
    print(f"SESSION_SECRET: {'SET' if session_secret != 'NOT_SET' else 'NOT_SET'}")
    print(f"DATABASE_URL: {'SET' if database_url != 'NOT_SET' else 'NOT_SET'}")
    
    # Tentar importar a aplicação
    try:
        from app import app
        print("✅ App importada com sucesso")
        
        with app.app_context():
            print("✅ Context da app funcionando")
            
        print("🎉 SAMAPE está saudável!")
        return 0
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
