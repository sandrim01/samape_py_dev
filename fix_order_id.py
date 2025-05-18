import os
from flask import Flask
from app import db
from models import ServiceOrder, equipment_service_orders

def update_order_id():
    """Atualiza o ID da ordem de serviço para 6"""
    # Encontre a ordem de serviço existente (ID 100)
    old_order = ServiceOrder.query.get(100)
    
    if not old_order:
        print("Ordem de serviço com ID 100 não encontrada.")
        return False
    
    # Verifique se já existe uma ordem com ID 6
    existing_order = ServiceOrder.query.get(6)
    if existing_order:
        print("Já existe uma ordem de serviço com ID 6. Não é possível atualizar.")
        return False
    
    print(f"Encontrada ordem de serviço ID {old_order.id} para cliente {old_order.client_id}")
    
    # Ajusta as relações na tabela de associação equipment_service_orders
    db.session.execute(
        f"UPDATE equipment_service_orders SET service_order_id = 6 WHERE service_order_id = {old_order.id}"
    )
    
    # Ajusta as relações nas imagens
    db.session.execute(
        f"UPDATE service_order_image SET service_order_id = 6 WHERE service_order_id = {old_order.id}"
    )
    
    # Ajusta as relações nas entradas financeiras
    db.session.execute(
        f"UPDATE financial_entry SET service_order_id = 6 WHERE service_order_id = {old_order.id}"
    )
    
    # Atualiza o ID da ordem de serviço via SQL direto (para evitar problemas com SQLAlchemy)
    db.session.execute(
        f"UPDATE service_order SET id = 6 WHERE id = {old_order.id}"
    )
    
    # Commit das alterações
    db.session.commit()
    
    print("ID da ordem de serviço atualizado com sucesso para 6.")
    return True

if __name__ == "__main__":
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    db.init_app(app)
    
    with app.app_context():
        update_order_id()