import re

def fix_log_calls(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    
    # Padrão para encontrar chamadas de log_action com formato errado
    pattern = r'log_action\(f[\'"](.*?): (.*?)[\'"]\)'
    
    # Mapeamento de tipos de entidade baseado na primeira parte da mensagem
    entity_type_map = {
        'Veículo editado': ('vehicle', 'vehicle.id'),
        'Veículo excluído': ('vehicle', 'vehicle_id'),
        'Imagem removida do veículo': ('vehicle', 'vehicle.id'),
        'Abastecimento registrado': ('refueling', 'refueling.id'),
        'Abastecimento editado': ('refueling', 'refueling.id'),
        'Abastecimento excluído': ('refueling', 'refueling_id'),
        'Comprovante removido do abastecimento': ('refueling', 'refueling.id'),
        'Manutenção registrada': ('maintenance', 'maintenance.id'),
        'Manutenção editada': ('maintenance', 'maintenance.id'),
        'Manutenção excluída': ('maintenance', 'maintenance_id'),
        'Nota fiscal removida da manutenção': ('maintenance', 'maintenance.id'),
        'Viagem iniciada': ('travel', 'travel_log.id'),
        'Viagem editada': ('travel', 'travel_log.id'),
        'Viagem finalizada': ('travel', 'travel_log.id'),
        'Viagem cancelada': ('travel', 'travel_log.id'),
        'Viagem excluída': ('travel', 'travel_log_id'),
    }
    
    def repl(match):
        action = match.group(1)
        details = match.group(2)
        
        # Tentar encontrar o tipo de entidade e o ID
        entity_type, entity_id = 'unknown', 'None'
        for key, (type_val, id_val) in entity_type_map.items():
            if key in action:
                entity_type = type_val
                entity_id = id_val
                break
        
        return f"log_action('{action}', '{entity_type}', {entity_id}, f'{details}')"
    
    # Substituir todas as ocorrências
    modified_content = re.sub(pattern, repl, content)
    
    with open(file_path, 'w') as file:
        file.write(modified_content)
    
    print(f"Arquivo {file_path} atualizado.")

# Executar a função para o arquivo de rotas
fix_log_calls('routes_vehicles.py')
