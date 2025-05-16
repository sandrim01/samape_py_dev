import os
import sys
from sqlalchemy import create_engine, text
from app import db
from models import Vehicle

print("Iniciando atualização da tabela vehicle...")

try:
    # Usando a conexão atual do banco de dados
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        print("Variável de ambiente DATABASE_URL não encontrada. Verifique suas variáveis de ambiente.")
        sys.exit(1)
    
    print(f"Conectando ao banco de dados...")
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    
    # Verificar se as colunas já existem para evitar erros
    result = connection.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'vehicle' AND column_name IN "
        "('image_data', 'image_filename', 'image_content_type', 'image_file_size')"
    ))
    existing_columns = [row[0] for row in result]
    
    # Adicionar as colunas necessárias se não existirem
    alterations = []
    
    if 'image_data' not in existing_columns:
        alterations.append("ADD COLUMN image_data BYTEA")
    
    if 'image_filename' not in existing_columns:
        alterations.append("ADD COLUMN image_filename VARCHAR(255)")
    
    if 'image_content_type' not in existing_columns:
        alterations.append("ADD COLUMN image_content_type VARCHAR(100)")
        
    if 'image_file_size' not in existing_columns:
        alterations.append("ADD COLUMN image_file_size INTEGER")
    
    # Executar as alterações
    if alterations:
        alter_sql = "ALTER TABLE vehicle " + ", ".join(alterations)
        print(f"Executando: {alter_sql}")
        connection.execute(text(alter_sql))
        connection.commit()
        print("Tabela atualizada com sucesso!")
    else:
        print("As colunas necessárias já existem na tabela. Nenhuma alteração necessária.")
    
    # Migrar imagens existentes
    # Se houver alguma imagem armazenada no sistema de arquivos que precisa ser migrada
    # esse seria o lugar para fazer isso

    connection.close()
    print("Operação concluída com sucesso!")

except Exception as e:
    print(f"Erro durante a atualização da tabela: {e}")
    sys.exit(1)