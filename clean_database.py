"""
Script para limpar o banco de dados mantendo apenas os usuários/funcionários
"""

from app import app, db
from sqlalchemy import text
from models import (
    User, Client, Equipment, ServiceOrder, FinancialEntry, ActionLog,
    UserRole, ServiceOrderStatus, FinancialEntryType, Supplier, Part, PartSale,
    SupplierOrder, OrderItem, OrderStatus, ServiceOrderImage
)

def clean_database():
    """Remove todos os dados exceto usuários/funcionários"""
    with app.app_context():
        try:
            print("Iniciando limpeza do banco de dados...")
            
            # Remover relações na tabela de associação equipment_service_orders
            print("Removendo associações entre equipamentos e ordens de serviço...")
            db.session.execute(text("DELETE FROM equipment_service_orders"))
            
            # Remover imagens de ordens de serviço primeiro (devido à chave estrangeira)
            print("Removendo imagens de ordens de serviço...")
            ServiceOrderImage.query.delete()
            
            # Remover itens de pedidos (devido à chave estrangeira)
            print("Removendo itens de pedidos de fornecedores...")
            OrderItem.query.delete()
            
            # Remover vendas de peças
            print("Removendo vendas de peças...")
            PartSale.query.delete()
            
            # Remover peças
            print("Removendo peças...")
            Part.query.delete()
            
            # Remover entradas financeiras
            print("Removendo entradas financeiras...")
            FinancialEntry.query.delete()
            
            # Remover ordens de serviço
            print("Removendo ordens de serviço...")
            ServiceOrder.query.delete()
            
            # Remover equipamentos
            print("Removendo equipamentos...")
            Equipment.query.delete()
            
            # Remover clientes
            print("Removendo clientes...")
            Client.query.delete()
            
            # Remover pedidos de fornecedores
            print("Removendo pedidos de fornecedores...")
            SupplierOrder.query.delete()
            
            # Remover fornecedores
            print("Removendo fornecedores...")
            Supplier.query.delete()
            
            # Remover logs de ações (opcional, mas ajuda a limpar o banco)
            print("Removendo logs de ações...")
            ActionLog.query.delete()
            
            # Comentamos o reset de sequências por enquanto devido a erros com nomes de sequências
            # print("Resetando sequências de IDs...")
            # Sequências serão resetadas automaticamente pelo PostgreSQL quando necessário
            
            db.session.commit()
            print("Limpeza do banco de dados concluída com sucesso!")
            
            # Exibir usuários mantidos
            users = User.query.all()
            print(f"\nUsuários mantidos ({len(users)}):")
            for user in users:
                print(f"- {user.username} ({user.name}, {user.role.value})")
            
        except Exception as e:
            db.session.rollback()
            print(f"Erro durante a limpeza do banco de dados: {str(e)}")

if __name__ == "__main__":
    clean_database()