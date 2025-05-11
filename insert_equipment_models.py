"""
Script para inserir principais modelos de maquinários de pedreiras e mineração no banco de dados.
"""
import os
import sys
from datetime import datetime
from app import app, db
from models import Client, Equipment

# Primeiro criamos um cliente genérico para associar os equipamentos
# (depois esses equipamentos podem ser reassociados aos clientes reais)
DEMO_CLIENT_NAME = "CLIENTE DEMONSTRAÇÃO"
DEMO_CLIENT_DOCUMENT = "00.000.000/0001-00"

equipment_data = [
    # Caterpillar
    {"brand": "Caterpillar", "type": "Escavadeira Hidráulica", "model": "CAT 336", "year": 2023},
    {"brand": "Caterpillar", "type": "Escavadeira Hidráulica", "model": "CAT 390F L", "year": 2023},
    {"brand": "Caterpillar", "type": "Pá Carregadeira", "model": "CAT 980", "year": 2022},
    {"brand": "Caterpillar", "type": "Pá Carregadeira", "model": "CAT 966K XE", "year": 2023},
    {"brand": "Caterpillar", "type": "Trator de Esteiras", "model": "CAT D9T", "year": 2022},
    {"brand": "Caterpillar", "type": "Caminhão Fora de Estrada", "model": "CAT 777E", "year": 2023},
    {"brand": "Caterpillar", "type": "Caminhão Articulado", "model": "CAT 745", "year": 2022},
    {"brand": "Caterpillar", "type": "Motoniveladora", "model": "CAT 140M3", "year": 2023},
    
    # JCB
    {"brand": "JCB", "type": "Retroescavadeira", "model": "JCB 3CX", "year": 2023},
    {"brand": "JCB", "type": "Retroescavadeira", "model": "JCB 4CX", "year": 2022},
    {"brand": "JCB", "type": "Escavadeira Hidráulica", "model": "JCB JS220", "year": 2023},
    {"brand": "JCB", "type": "Escavadeira Hidráulica", "model": "JCB JS370", "year": 2022},
    {"brand": "JCB", "type": "Pá Carregadeira", "model": "JCB 457", "year": 2023},
    {"brand": "JCB", "type": "Manipulador Telescópico", "model": "JCB 540-170", "year": 2022},
    
    # Volvo
    {"brand": "Volvo", "type": "Escavadeira Hidráulica", "model": "Volvo EC350E", "year": 2023},
    {"brand": "Volvo", "type": "Escavadeira Hidráulica", "model": "Volvo EC480E", "year": 2022},
    {"brand": "Volvo", "type": "Pá Carregadeira", "model": "Volvo L150H", "year": 2023},
    {"brand": "Volvo", "type": "Pá Carregadeira", "model": "Volvo L220H", "year": 2022},
    {"brand": "Volvo", "type": "Caminhão Articulado", "model": "Volvo A40G", "year": 2023},
    {"brand": "Volvo", "type": "Caminhão Articulado", "model": "Volvo A60H", "year": 2022},
    
    # Komatsu
    {"brand": "Komatsu", "type": "Escavadeira Hidráulica", "model": "Komatsu PC360LC-11", "year": 2023},
    {"brand": "Komatsu", "type": "Escavadeira Hidráulica", "model": "Komatsu PC490LC-11", "year": 2022},
    {"brand": "Komatsu", "type": "Pá Carregadeira", "model": "Komatsu WA500-8", "year": 2023},
    {"brand": "Komatsu", "type": "Trator de Esteiras", "model": "Komatsu D155AX-8", "year": 2022},
    {"brand": "Komatsu", "type": "Caminhão Fora de Estrada", "model": "Komatsu HD785-8", "year": 2023},
    {"brand": "Komatsu", "type": "Motoniveladora", "model": "Komatsu GD655-7", "year": 2022},
    
    # Liebherr
    {"brand": "Liebherr", "type": "Escavadeira Hidráulica", "model": "Liebherr R 976", "year": 2023},
    {"brand": "Liebherr", "type": "Escavadeira Hidráulica", "model": "Liebherr R 9400", "year": 2022},
    {"brand": "Liebherr", "type": "Pá Carregadeira", "model": "Liebherr L 566 XPower", "year": 2023},
    {"brand": "Liebherr", "type": "Pá Carregadeira", "model": "Liebherr L 586 XPower", "year": 2022},
    {"brand": "Liebherr", "type": "Escavadeira de Mineração", "model": "Liebherr R 9800", "year": 2023},
    {"brand": "Liebherr", "type": "Caminhão Fora de Estrada", "model": "Liebherr T 264", "year": 2022},
    
    # Case
    {"brand": "Case", "type": "Retroescavadeira", "model": "Case 580N", "year": 2023},
    {"brand": "Case", "type": "Escavadeira Hidráulica", "model": "Case CX350D", "year": 2022},
    {"brand": "Case", "type": "Pá Carregadeira", "model": "Case 921G", "year": 2023},
    {"brand": "Case", "type": "Motoniveladora", "model": "Case 865B", "year": 2022},
    {"brand": "Case", "type": "Trator de Esteiras", "model": "Case 2050M", "year": 2023},
    
    # John Deere
    {"brand": "John Deere", "type": "Escavadeira Hidráulica", "model": "John Deere 380G LC", "year": 2023},
    {"brand": "John Deere", "type": "Pá Carregadeira", "model": "John Deere 844K", "year": 2022},
    {"brand": "John Deere", "type": "Motoniveladora", "model": "John Deere 872G", "year": 2023},
    {"brand": "John Deere", "type": "Trator de Esteiras", "model": "John Deere 950K", "year": 2022},
    {"brand": "John Deere", "type": "Caminhão Articulado", "model": "John Deere 410E", "year": 2023},
]

def insert_equipment_models():
    """Insere modelos de equipamentos no banco de dados"""
    
    print("Iniciando inserção de modelos de equipamentos de mineração e pedreiras...")
    
    with app.app_context():
        # Verifica se o cliente demo já existe
        demo_client = Client.query.filter_by(document=DEMO_CLIENT_DOCUMENT).first()
        
        if not demo_client:
            print(f"Criando cliente demonstração: {DEMO_CLIENT_NAME}...")
            demo_client = Client(
                name=DEMO_CLIENT_NAME,
                document=DEMO_CLIENT_DOCUMENT,
                email="demo@exemplo.com.br",
                phone="(11) 99999-9999",
                address="Av. Demonstração, 1000, São Paulo - SP",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(demo_client)
            db.session.commit()
            print(f"Cliente demonstração criado com ID: {demo_client.id}")
        else:
            print(f"Cliente demonstração já existe com ID: {demo_client.id}")
        
        # Conta equipamentos inseridos
        count = 0
        # Conta equipamentos que já existiam
        existing_count = 0
        
        for equipment in equipment_data:
            # Verifica se já existe pela combinação de marca, modelo e tipo
            existing = Equipment.query.filter_by(
                brand=equipment["brand"],
                model=equipment["model"],
                type=equipment["type"]
            ).first()
            
            if existing:
                print(f"Equipamento já existe: {equipment['brand']} {equipment['model']}")
                existing_count += 1
                continue
            
            serial_number = f"{equipment['brand'][:3]}{equipment['model'][:3]}{equipment['year']}{count:03d}"
            
            new_equipment = Equipment(
                client_id=demo_client.id,
                type=equipment["type"],
                brand=equipment["brand"],
                model=equipment["model"],
                serial_number=serial_number,
                year=equipment["year"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(new_equipment)
            count += 1
            
            # Commit a cada 10 inserções para evitar transações muito grandes
            if count % 10 == 0:
                db.session.commit()
                print(f"Inseridos {count} equipamentos até agora...")
        
        # Commit final para garantir que todos os registros foram salvos
        db.session.commit()
        
        print(f"Inserção concluída: {count} novos equipamentos inseridos.")
        print(f"Equipamentos que já existiam: {existing_count}")
        print(f"Total de equipamentos no catálogo: {count + existing_count}")

if __name__ == "__main__":
    insert_equipment_models()