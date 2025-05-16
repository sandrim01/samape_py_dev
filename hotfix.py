"""
Script para corrigir problemas específicos no banco de dados
"""
import os
import sys
from sqlalchemy import create_engine, text

# Configuração do banco de dados
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:qUngJAyBvLWQdkmSkZEjjEoMoDVzOBnx@trolley.proxy.rlwy.net:22285/railway")

def verificar_e_corrigir_coluna_image():
    """Verifica e corrige problemas com colunas da tabela vehicle"""
    try:
        print(f"Conectando ao banco de dados...")
        engine = create_engine(DATABASE_URL)
        connection = engine.connect()
        
        # Verificar se a coluna image existe
        result = connection.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'vehicle' AND column_name = 'image'"
        ))
        
        if not list(result):
            print("Coluna 'image' não encontrada. Adicionando...")
            connection.execute(text("ALTER TABLE vehicle ADD COLUMN image VARCHAR(255)"))
            print("Coluna 'image' adicionada com sucesso!")
        else:
            print("Coluna 'image' já existe. Tudo certo!")
            
        # Verificar se há linhas com valores NULL na coluna image onde image_filename não é NULL
        result = connection.execute(text(
            "SELECT COUNT(*) FROM vehicle "
            "WHERE image IS NULL AND image_filename IS NOT NULL"
        ))
        count = result.scalar()
        
        if count > 0:
            print(f"Encontradas {count} linhas com 'image' NULL que possuem 'image_filename'. Atualizando...")
            connection.execute(text(
                "UPDATE vehicle SET image = image_filename "
                "WHERE image IS NULL AND image_filename IS NOT NULL"
            ))
            print("Linhas atualizadas com sucesso!")
            
        # Fechar conexão
        connection.close()
        print("Operação concluída com sucesso!")
        return True
        
    except Exception as e:
        print(f"Erro: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando script de hotfix...")
    if verificar_e_corrigir_coluna_image():
        print("Hotfix aplicado com sucesso!")
        sys.exit(0)
    else:
        print("Falha ao aplicar hotfix.")
        sys.exit(1)