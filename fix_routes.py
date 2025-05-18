#!/usr/bin/env python3
import re

# Ler conteúdo do arquivo
with open('routes.py', 'r') as f:
    content = f.read()

# Substituir a função view_service_order_alt por uma versão simplificada
pattern = r'(@app\.route\(\'/ordem/<int:id>/visualizar\'\)\s+@login_required\s+def view_service_order_alt\(id\):).*?(?=\s+@app\.route|\Z)'
replacement = r"""\1
        # Redirecionar para a implementação principal
        return redirect(url_for('view_service_order', id=id))
"""

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Salvar as alterações
with open('routes.py', 'w') as f:
    f.write(new_content)
    print("Função view_service_order_alt atualizada")

# Corrigir o template usado na função de login
with open('routes.py', 'r') as f:
    content = f.read()

# Substituir o template utilizado na função de login
content = content.replace("return render_template('login.html', form=form)", "return render_template('login_standalone.html', form=form)")
content = content.replace("return render_template('standalone_login.html', form=form)", "return render_template('login_standalone.html', form=form)")

with open('routes.py', 'w') as f:
    f.write(content)
    print("Template de login atualizado")
