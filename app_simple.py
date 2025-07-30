#!/usr/bin/env python3
"""
Versão simplificada do app.py para Railway
Remove todas as validações que podem impedir a inicialização
"""

import os
import secrets
from flask import Flask, render_template, redirect, url_for

# Configuração mínima necessária
app = Flask(__name__)

# Configurações básicas com fallbacks
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///samape.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Rota de teste básica
@app.route('/')
def index():
    return '''
    <html>
        <head><title>SAMAPE - Status Railway</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>🚂 SAMAPE Railway - Funcionando!</h1>
            <p><strong>Status:</strong> ✅ Aplicação inicializada com sucesso</p>
            <p><strong>Ambiente:</strong> ''' + os.environ.get('FLASK_ENV', 'development') + '''</p>
            <p><strong>Porta:</strong> ''' + os.environ.get('PORT', '5000') + '''</p>
            <p><strong>SESSION_SECRET:</strong> ''' + ('✅ Configurada' if os.environ.get('SESSION_SECRET') else '⚠️ Usando fallback') + '''</p>
            <p><strong>DATABASE_URL:</strong> ''' + ('✅ Configurada' if os.environ.get('DATABASE_URL') else '⚠️ Usando SQLite local') + '''</p>
            <hr>
            <h2>Próximos Passos:</h2>
            <ol>
                <li>Configure SESSION_SECRET no Railway</li>
                <li>Ative PostgreSQL e configure DATABASE_URL</li>
                <li>A aplicação completa será carregada automaticamente</li>
            </ol>
            <p><em>Esta é uma versão temporária para verificar se Railway está funcionando.</em></p>
        </body>
    </html>
    '''

@app.route('/health')
def health():
    return {'status': 'ok', 'app': 'SAMAPE', 'railway': True}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚂 Iniciando SAMAPE Railway na porta {port}")
    print(f"🌐 URL: https://samape-py-samapedev.up.railway.app/")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
