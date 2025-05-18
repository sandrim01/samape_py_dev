#!/usr/bin/env python3

# Criar um arquivo routes.py completamente novo
content = """
# Importações
from flask import render_template, redirect, url_for
from app import app
from routes_original import register_routes

# Adicionar uma rota simples para redirecionamento
@app.route('/ordem/<int:id>/visualizar')
def view_service_order_alt(id):
    return redirect(url_for('view_service_order', id=id))

# Registrar todas as outras rotas
register_routes(app)
"""

# Renomear o arquivo routes.py atual para routes_original.py
import os
if os.path.exists('routes.py'):
    os.rename('routes.py', 'routes_original.py')
    print("Arquivo routes.py original renomeado para routes_original.py")

# Criar o novo arquivo routes.py
with open('routes.py', 'w') as f:
    f.write(content)
    print("Novo arquivo routes.py criado com sucesso")

# Modificar o arquivo app.py para usar a nova abordagem
with open('app.py', 'r') as f:
    app_content = f.read()

# Substituir a linha que importa register_routes
import re
new_app_content = re.sub(
    r'from routes import register_routes',
    '# As rotas são importadas diretamente em main.py',
    app_content
)

new_app_content = re.sub(
    r'register_routes\(app\)',
    '# register_routes é chamado em routes.py',
    new_app_content
)

with open('app.py', 'w') as f:
    f.write(new_app_content)
    print("Arquivo app.py atualizado")

print("Correção aplicada com sucesso!")
