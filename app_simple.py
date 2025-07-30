#!/usr/bin/env python3
"""
Versão simplificada do app.py para Railway
Remove todas as validações que podem impedir a inicialização
"""

import os
import secrets
from flask import Flask

# Configuração mínima necessária
app = Flask(__name__)

# Configurações básicas com fallbacks
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', secrets.token_hex(32))

# Usar a URL do PostgreSQL fornecida
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:fzsZiDkvLIsSlVGzrOyEbgWTStUvfsQA@centerbeam.proxy.rlwy.net:51097/railway')
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Função para testar banco
def test_database():
    """Testa se o banco está respondendo"""
    try:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] == 1
    except Exception as e:
        return f"Erro: {str(e)}"

# Rota de teste básica
@app.route('/')
def index():
    # Testar banco
    db_status = test_database()
    db_ok = db_status is True
    
    return f'''
    <html>
        <head><title>SAMAPE - Diagnóstico Railway</title></head>
        <body style="font-family: Arial; padding: 20px; background: {'#e8f5e8' if db_ok else '#ffe8e8'};">
            <h1>🚂 SAMAPE Railway - Diagnóstico</h1>
            
            <h2>📊 Status da Aplicação:</h2>
            <p><strong>Status:</strong> ✅ Aplicação inicializada</p>
            <p><strong>Ambiente:</strong> {os.environ.get('FLASK_ENV', 'development')}</p>
            <p><strong>Porta:</strong> {os.environ.get('PORT', '5000')}</p>
            
            <h2>🔐 Configurações:</h2>
            <p><strong>SESSION_SECRET:</strong> {'✅ Configurada' if os.environ.get('SESSION_SECRET') else '⚠️ Usando fallback'}</p>
            <p><strong>DATABASE_URL:</strong> {'✅ Configurada' if os.environ.get('DATABASE_URL') else '⚠️ Usando fallback'}</p>
            
            <h2>🗄️ Status do Banco PostgreSQL:</h2>
            <p style="padding: 10px; border-radius: 5px; background: {'#d4edda' if db_ok else '#f8d7da'};">
                <strong>Conexão:</strong> {'✅ FUNCIONANDO' if db_ok else f'❌ ERRO: {db_status}'}
            </p>
            
            {'''
            <h2>🎉 BANCO FUNCIONANDO!</h2>
            <p>O PostgreSQL está respondendo corretamente. O problema pode estar na aplicação principal.</p>
            <h3>✅ Próximos Passos:</h3>
            <ol>
                <li>Configure todas as variáveis no Railway</li>
                <li>Volte para app.py completo</li>
                <li>A aplicação deve funcionar normalmente</li>
            </ol>
            ''' if db_ok else '''
            <h2>💥 PROBLEMA NO BANCO!</h2>
            <p>O PostgreSQL não está respondendo. Isso explica o erro 502.</p>
            <h3>🔧 Soluções:</h3>
            <ol>
                <li>Verifique se PostgreSQL está ativo no Railway</li>
                <li>Confirme se a DATABASE_URL está correta</li>
                <li>Tente recriar o banco no Railway</li>
            </ol>
            '''}
            
            <hr>
            <p><strong>URL do Banco:</strong> {DATABASE_URL[:50]}...{DATABASE_URL[-20:]}</p>
            <p><em>Diagnóstico automático - {('Tudo OK!' if db_ok else 'Problema identificado')}</em></p>
        </body>
    </html>
    '''

@app.route('/health')
def health():
    db_status = test_database()
    return {
        'status': 'ok' if db_status is True else 'error',
        'app': 'SAMAPE',
        'railway': True,
        'database': 'connected' if db_status is True else 'failed',
        'database_error': str(db_status) if db_status is not True else None
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚂 Iniciando SAMAPE Railway na porta {port}")
    print(f"🌐 URL: https://samape-py-samapedev.up.railway.app/")
    print(f"🗄️ Banco: {DATABASE_URL[:50]}...{DATABASE_URL[-20:]}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
