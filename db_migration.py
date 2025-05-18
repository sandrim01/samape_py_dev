from app import db
from models import ServiceOrder
from sqlalchemy import text

# Função para verificar se a coluna já existe
def column_exists(table_name, column_name):
    query = text(f"SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name='{table_name}' AND column_name='{column_name}');")
    result = db.session.execute(query).scalar()
    return result

# Migração de banco de dados - adicionar colunas de cálculo R$/KM
def migrate_database():
    print("Iniciando migração de banco de dados...")
    
    # Verificar e adicionar a coluna distance_km se não existir
    if not column_exists('service_order', 'distance_km'):
        print("Adicionando coluna distance_km à tabela service_order...")
        db.session.execute(text("ALTER TABLE service_order ADD COLUMN distance_km NUMERIC(10, 2);"))
    
    # Verificar e adicionar a coluna cost_per_km se não existir
    if not column_exists('service_order', 'cost_per_km'):
        print("Adicionando coluna cost_per_km à tabela service_order...")
        db.session.execute(text("ALTER TABLE service_order ADD COLUMN cost_per_km NUMERIC(10, 2);"))
    
    # Verificar e adicionar a coluna total_distance_cost se não existir
    if not column_exists('service_order', 'total_distance_cost'):
        print("Adicionando coluna total_distance_cost à tabela service_order...")
        db.session.execute(text("ALTER TABLE service_order ADD COLUMN total_distance_cost NUMERIC(10, 2);"))
    
    # Commit das alterações
    db.session.commit()
    print("Migração concluída com sucesso!")

if __name__ == "__main__":
    from app import app
    with app.app_context():
        migrate_database()