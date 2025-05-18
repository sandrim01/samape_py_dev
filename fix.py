#!/usr/bin/env python3
"""
Script para corrigir o problema de sintaxe no arquivo routes.py
"""

with open('routes.py', 'r') as file:
    content = file.readlines()

# Encontrar a definição da função view_service_order_alt
start_line = 0
end_line = 0
for i, line in enumerate(content):
    if 'def view_service_order_alt(' in line:
        start_line = i
        break

# Buscar o fim da função
if start_line > 0:
    # Substituir a função por uma versão simples que apenas redireciona
    correct_function = [
        content[start_line-2],  # @app.route line
        content[start_line-1],  # @login_required line
        content[start_line],    # def view_service_order_alt line
        "    # Simplesmente redireciona para a implementação principal\n",
        "    return redirect(url_for('view_service_order', id=id))\n",
        "\n"
    ]
    
    # Encontrar onde a próxima função começa (procurando pela próxima linha com @app.route)
    for i in range(start_line + 1, len(content)):
        if '@app.route' in content[i]:
            end_line = i - 1
            break
    
    # Se não encontramos o fim, assumimos que vai até o final
    if end_line == 0:
        end_line = len(content)
    
    # Substituir a função problemática pela corrigida
    new_content = content[:start_line-2] + correct_function + content[end_line:]
    
    # Escrever o arquivo corrigido
    with open('routes.py', 'w') as file:
        file.writelines(new_content)
    
    print(f"Função view_service_order_alt corrigida nas linhas {start_line-2} até {end_line}")
else:
    print("Função view_service_order_alt não encontrada no arquivo")
