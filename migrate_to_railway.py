import os
import sys
from sqlalchemy import create_engine, Table, MetaData, text
from sqlalchemy.orm import sessionmaker
from app import db
from models import (
    User, Client, Equipment, ServiceOrder, FinancialEntry, ActionLog,
    UserRole, ServiceOrderStatus, FinancialEntryType, Supplier, Part, PartSale,
    SupplierOrder, OrderItem, OrderStatus, ServiceOrderImage, LoginAttempt,
    SystemSettings, SequenceCounter
)

# Configuração do banco de dados
SOURCE_DB_URL = os.environ.get("DATABASE_URL")
if not SOURCE_DB_URL:
    print("Variável de ambiente DATABASE_URL não encontrada. Verifique suas variáveis de ambiente.")
    sys.exit(1)

TARGET_DB_URL = "postgresql://postgres:qUngJAyBvLWQdkmSkZEjjEoMoDVzOBnx@trolley.proxy.rlwy.net:22285/railway"

print("Iniciando migração de dados para o Railway...")
print(f"Banco de dados de origem: {SOURCE_DB_URL}")
print(f"Banco de dados de destino: {TARGET_DB_URL}")

# Conectar ao banco de dados de origem
source_engine = create_engine(SOURCE_DB_URL)
SourceSession = sessionmaker(bind=source_engine)
source_session = SourceSession()

# Conectar ao banco de dados de destino
target_engine = create_engine(TARGET_DB_URL)
TargetSession = sessionmaker(bind=target_engine)
target_session = TargetSession()

# Verificar conexão com os bancos de dados
try:
    # Testar conexão ao banco de origem
    source_session.execute(text("SELECT 1"))
    print("Conexão com o banco de dados de origem estabelecida com sucesso.")
    
    # Testar conexão ao banco de destino
    target_session.execute(text("SELECT 1"))
    print("Conexão com o banco de dados de destino estabelecida com sucesso.")
except Exception as e:
    print(f"Erro ao conectar aos bancos de dados: {e}")
    sys.exit(1)

# Criar todas as tabelas no banco de dados de destino
print("Criando estrutura de tabelas no banco de dados de destino...")
# Usando a definição de tabelas do SQLAlchemy que já existe no aplicativo
from app import app
with app.app_context():
    # Criar todas as tabelas no banco de destino
    # Usando sqlalchemy diretamente
    from models import Base
    Base.metadata.create_all(target_engine)

print("Estrutura de tabelas criada no banco de dados de destino.")

# Lista de modelos para migrar com ordem específica (tabelas com chaves primárias primeiro)
models = [
    User,  # Usuários devem vir primeiro por causa de foreign keys
    Client,  
    Supplier,
    SystemSettings,
    SequenceCounter,
    LoginAttempt,
    ActionLog,
    Equipment,
    ServiceOrder,  
    ServiceOrderImage,
    FinancialEntry,
    Part,
    PartSale,
    SupplierOrder,
    OrderItem
]

# Limpar os dados existentes no banco de destino para evitar conflitos
print("Limpando dados existentes no banco de destino...")
try:
    with app.app_context():
        for model in reversed(models):  # Reverso para remover tabelas com chaves estrangeiras primeiro
            print(f"Removendo registros de {model.__name__}...")
            target_session.query(model).delete()
        target_session.commit()
    print("Dados existentes limpos com sucesso.")
except Exception as e:
    print(f"Erro ao limpar dados existentes: {e}")
    target_session.rollback()

# Tabela de junção especial
equipment_service_orders = Table(
    'equipment_service_orders',
    MetaData(),
    autoload_with=source_engine
)

try:
    # Migrar dados para cada modelo
    for model in models:
        print(f"Migrando dados para {model.__name__}...")
        
        # Ler todos os registros do banco de dados de origem
        try:
            records = list(source_session.query(model).all())
            print(f"  Encontrados {len(records)} registros para {model.__name__}.")
        except Exception as e:
            print(f"  Erro ao ler registros de {model.__name__}: {e}")
            continue
        
        # Criar novos registros no banco de dados de destino
        if records:
            for i, record in enumerate(records):
                try:
                    # Criar um dicionário com os dados do registro
                    record_dict = {c.name: getattr(record, c.name) for c in model.__table__.columns}
                    
                    # Criar um novo objeto com os mesmos dados
                    new_record = model(**record_dict)
                    
                    # Adicionar o novo registro ao banco de dados de destino
                    target_session.add(new_record)
                    
                    # Commit a cada 100 registros para evitar consumo excessivo de memória
                    if i > 0 and i % 100 == 0:
                        target_session.commit()
                        print(f"    Progresso: {i}/{len(records)} registros")
                except Exception as e:
                    print(f"  Erro ao migrar registro {i} de {model.__name__}: {e}")
                    target_session.rollback()
            
            # Commit final para o modelo
            try:
                target_session.commit()
                print(f"  {len(records)} registros migrados para {model.__name__}.")
            except Exception as e:
                print(f"  Erro no commit final de {model.__name__}: {e}")
                target_session.rollback()
        else:
            print(f"  Nenhum registro encontrado para {model.__name__}.")
    
    # Migrar dados da tabela de junção equipment_service_orders
    print("Migrando dados para equipment_service_orders...")
    try:
        equipment_so_records = list(source_session.execute(equipment_service_orders.select()).fetchall())
        
        if equipment_so_records:
            # Primeiro, limpar registros existentes
            target_session.execute(equipment_service_orders.delete())
            
            # Agora inserir os novos registros
            for i, record in enumerate(equipment_so_records):
                try:
                    # Inserir diretamente na tabela de junção no banco de destino
                    target_session.execute(
                        equipment_service_orders.insert().values(
                            equipment_id=record.equipment_id,
                            service_order_id=record.service_order_id
                        )
                    )
                    
                    # Commit a cada 100 registros
                    if i > 0 and i % 100 == 0:
                        target_session.commit()
                        print(f"    Progresso: {i}/{len(equipment_so_records)} registros")
                except Exception as e:
                    print(f"  Erro ao migrar relacionamento equipment_service_orders {i}: {e}")
                    continue
            
            target_session.commit()
            print(f"  {len(equipment_so_records)} registros migrados para equipment_service_orders.")
        else:
            print("  Nenhum registro encontrado para equipment_service_orders.")
    except Exception as e:
        print(f"Erro ao migrar tabela de junção equipment_service_orders: {e}")
    
    print("\nMigração concluída com sucesso!")

except Exception as e:
    print(f"Erro durante a migração: {e}")
    target_session.rollback()
    sys.exit(1)

finally:
    source_session.close()
    target_session.close()

print("\nRecomendações:")
print("1. Atualize a variável de ambiente DATABASE_URL do Replit para apontar para o novo banco de dados")
print("2. Teste a aplicação para verificar se a conexão com o novo banco está funcionando corretamente")
print("3. Faça backup periódico do seu banco de dados")