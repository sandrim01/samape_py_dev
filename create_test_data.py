"""
Script para criar dados de teste no sistema.
Cria um cliente, uma ordem de serviço e uma nota fiscal.
"""
from datetime import datetime
from decimal import Decimal

from app import db
from models import Client, Equipment, ServiceOrder, ServiceOrderStatus, User, UserRole

def create_test_data():
    """Cria dados de teste no sistema."""
    print("Criando dados de teste...")
    
    # Verificar se já existe um cliente
    client = Client.query.first()
    if not client:
        print("Criando cliente de teste...")
        client = Client(
            name="Cliente Teste SAMAPE",
            document="123.456.789-00",
            email="cliente@teste.com",
            phone="(11) 98765-4321",
            address="Rua Teste, 123 - São Paulo/SP"
        )
        db.session.add(client)
        db.session.commit()
    
    # Verificar se já existe um usuário admin
    admin = User.query.filter_by(username="admin").first()
    if not admin:
        print("Criando usuário admin...")
        admin = User(
            username="admin",
            name="Administrador",
            email="admin@samape.com",
            role=UserRole.admin,
            active=True
        )
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()
    
    # Verificar se já existe um equipamento para o cliente
    equipment = Equipment.query.filter_by(client_id=client.id).first()
    if not equipment:
        print("Criando equipamento de teste...")
        equipment = Equipment(
            client_id=client.id,
            type="Escavadeira",
            brand="Caterpillar",
            model="320D",
            serial_number="CAT320D-12345",
            year=2022
        )
        db.session.add(equipment)
        db.session.commit()
    
    # Verificar se já existe uma ordem de serviço fechada
    service_order = ServiceOrder.query.filter_by(
        client_id=client.id,
        status=ServiceOrderStatus.fechada
    ).first()
    
    if not service_order:
        print("Criando ordem de serviço fechada...")
        # Criar OS com status fechada
        service_order = ServiceOrder(
            client_id=client.id,
            responsible_id=admin.id if admin else None,
            description="Manutenção preventiva na escavadeira",
            status=ServiceOrderStatus.fechada,
            invoice_number="NF-TEST-001",
            invoice_date=datetime.utcnow(),
            invoice_amount=Decimal("1500.00"),
            service_details="Realizada manutenção preventiva conforme manual do fabricante. Substituídos filtros e óleo hidráulico.",
            closed_at=datetime.utcnow()
        )
        db.session.add(service_order)
        db.session.flush()  # Atribuir ID antes de adicionar equipamento
        
        # Associar equipamento à OS
        if equipment:
            service_order.equipment.append(equipment)
        
        db.session.commit()
        print(f"Ordem de serviço #{service_order.id} criada com sucesso!")
    else:
        print(f"Ordem de serviço #{service_order.id} já existe.")
    
    print("Dados de teste criados com sucesso!")
    return True

if __name__ == "__main__":
    # Este arquivo pode ser executado diretamente
    from flask import Flask
    from app import db
    
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:qUngJAyBvLWQdkmSkZEjjEoMoDVzOBnx@trolley.proxy.rlwy.net:22285/railway"
    db.init_app(app)
    
    with app.app_context():
        create_test_data()