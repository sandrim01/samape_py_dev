#!/usr/bin/env python3

with open('routes.py', 'r') as file:
    lines = file.readlines()

# Corrigir a função view_service_order_alt
for i, line in enumerate(lines):
    if 'def view_service_order_alt' in line:
        # Encontramos a função, vamos garantir que ela esteja correta
        correct_implementation = [
            '    @app.route(\'/ordem/<int:id>/visualizar\')\n',
            '    @login_required\n',
            '    def view_service_order_alt(id):\n',
            '        # Redirecionar para a implementação principal\n',
            '        return redirect(url_for(\'view_service_order\', id=id))\n',
            '\n'
        ]
        
        # Substituir as linhas da função
        start_idx = i - 2  # Pegamos as duas linhas de decoradores também
        # Substituir até encontrar uma linha sem espaço no início ou fim de arquivo
        end_idx = start_idx
        while end_idx < len(lines) and (lines[end_idx].strip() == '' or lines[end_idx].startswith(' ')):
            end_idx += 1
        
        # Substituir as linhas originais pelas corrigidas
        lines[start_idx:end_idx] = correct_implementation

# Salvar as alterações
with open('routes.py.fixed', 'w') as file:
    file.writelines(lines)

print("Arquivo corrigido gerado: routes.py.fixed")
