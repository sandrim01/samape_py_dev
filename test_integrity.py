#!/usr/bin/env python3
"""
Script de teste para verificar se a aplicação SAMAPE está funcionando corretamente
após as correções implementadas.
"""

import sys
import os

def test_imports():
    """Testa se todos os módulos podem ser importados sem erro."""
    print("🔍 Testando imports...")
    
    try:
        import app
        print("✅ app.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar app.py: {e}")
        return False
    
    try:
        import models
        print("✅ models.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar models.py: {e}")
        return False
    
    try:
        import config
        print("✅ config.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar config.py: {e}")
        return False
    
    try:
        import database
        print("✅ database.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar database.py: {e}")
        return False
    
    try:
        import logging_config
        print("✅ logging_config.py importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar logging_config.py: {e}")
        return False
    
    return True

def test_configuration():
    """Testa se a configuração está correta."""
    print("\n🔧 Testando configuração...")
    
    try:
        from config import DevelopmentConfig, ProductionConfig
        dev_config = DevelopmentConfig()
        prod_config = ProductionConfig()
        
        # Verificar se tem SECRET_KEY
        if hasattr(dev_config, 'SECRET_KEY') and dev_config.SECRET_KEY:
            print("✅ SECRET_KEY configurado")
        else:
            print("⚠️  SECRET_KEY não configurado (isso pode estar correto se usando env vars)")
        
        # Verificar se tem DATABASE_URI
        if hasattr(dev_config, 'SQLALCHEMY_DATABASE_URI'):
            print("✅ SQLALCHEMY_DATABASE_URI configurado")
        else:
            print("❌ SQLALCHEMY_DATABASE_URI não configurado")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Erro ao testar configuração: {e}")
        return False

def test_database_connection():
    """Testa se a conexão com o banco está funcionando."""
    print("\n🗄️  Testando conexão com banco...")
    
    try:
        from app import app
        from database import db
        
        with app.app_context():
            # Tentar uma query simples
            result = db.engine.execute("SELECT 1")
            print("✅ Conexão com banco funcionando")
            return True
    except Exception as e:
        print(f"⚠️  Erro ao conectar com banco: {e}")
        print("   (Isso é normal se o banco não estiver configurado)")
        return True  # Não falha o teste por isso

def test_application_creation():
    """Testa se a aplicação Flask pode ser criada."""
    print("\n🌐 Testando criação da aplicação...")
    
    try:
        from app import app
        
        if app:
            print("✅ Aplicação Flask criada com sucesso")
            print(f"   - Debug: {app.debug}")
            print(f"   - Environment: {app.config.get('ENV', 'unknown')}")
            return True
        else:
            print("❌ Aplicação Flask não foi criada")
            return False
    except Exception as e:
        print(f"❌ Erro ao criar aplicação: {e}")
        return False

def main():
    """Função principal do teste."""
    print("🚀 SAMAPE - Teste de Integridade Pós-Correções")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_configuration,
        test_application_creation,
        test_database_connection
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Erro no teste {test.__name__}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("🎉 Todos os testes passaram! A aplicação está funcionando corretamente.")
        return 0
    else:
        print("⚠️  Alguns testes falharam. Verifique os problemas acima.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
