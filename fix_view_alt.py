import os

# Criar a versão correta da função view_service_order_alt
corrected_function = """
    @app.route('/ordem/<int:id>/visualizar')
    @login_required
    def view_service_order_alt(id):
        # Simplesmente redireciona para a implementação principal
        return redirect(url_for('view_service_order', id=id))
"""

# Ler o arquivo routes.py
with open('routes.py', 'r') as file:
    content = file.read()

# Procurar por um padrão específico que identifique a função view_service_order_alt
import re
pattern = r'@app\.route\(\'/ordem/<int:id>/visualizar\'\)(.*?)def view_service_order_alt\(id\):.*?(?=@app\.route|$)'
replacement = corrected_function

# Realizar a substituição no conteúdo (usando re.DOTALL para corresponder a várias linhas)
updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Escrever o conteúdo atualizado de volta ao arquivo
with open('routes.py.fixed', 'w') as file:
    file.write(updated_content)

print("Arquivo routes.py.fixed criado com a função view_service_order_alt corrigida.")
