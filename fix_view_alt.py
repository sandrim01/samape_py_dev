#!/usr/bin/env python3
# Script para simplificar a rota view_service_order_alt no arquivo routes.py

import re

with open('routes.py', 'r') as file:
    content = file.read()

# Expressão regular para encontrar toda a função view_service_order_alt
pattern = r'@app\.route\(\'/ordem/<int:id>/visualizar\'\)\s+@login_required\s+def view_service_order_alt\(id\):.*?return render_template\(.*?\)'
replacement = """@app.route('/ordem/<int:id>/visualizar')
    @login_required
    def view_service_order_alt(id):
        # Redirecionar para a implementação principal
        return redirect(url_for('view_service_order', id=id))"""

# Substituir usando regex com flag DOTALL para considerar múltiplas linhas
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Escrever o resultado em um arquivo temporário
with open('routes.py.fixed', 'w') as file:
    file.write(new_content)

print("Arquivo routes.py.fixed gerado com sucesso.")
