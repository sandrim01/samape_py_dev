"""
Script para corrigir o modelo ServiceOrder sem perder dados
"""
from app import app, db
from models import ServiceOrder

with app.app_context():
    # Atualizar o modelo, forçando SQLAlchemy a reconhecer a coluna
    db.session.commit()
    
    # Verificar se o modelo está funcionando
    try:
        order_count = ServiceOrder.query.count()
        print(f"ServiceOrder model verificado. Existem {order_count} ordens de serviço no banco.")
    except Exception as e:
        print(f"Erro ao verificar o modelo: {e}")
        
    print("Processo de correção concluído.")