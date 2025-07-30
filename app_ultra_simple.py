#!/usr/bin/env python3
"""
Versão ULTRA SIMPLES para Railway - apenas Flask puro
Sem SQLAlchemy, sem psycopg2, sem dependências complexas
"""

import os
from flask import Flask

# Aplicação mínima
app = Flask(__name__)
app.config['SECRET_KEY'] = 'temporary-key-for-railway-test'

@app.route('/')
def home():
    """Página inicial básica"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>SAMAPE Railway - Status</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial; margin: 40px; background: #f5f5f5; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .success { color: #28a745; }
            .warning { color: #ffc107; }
            .error { color: #dc3545; }
            .info { background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="success">🎉 SAMAPE Railway - FUNCIONANDO!</h1>
            
            <div class="info">
                <h2>📊 Status da Aplicação:</h2>
                <p><strong>Status:</strong> <span class="success">✅ Online e Respondendo</span></p>
                <p><strong>Servidor:</strong> Railway</p>
                <p><strong>Porta:</strong> ''' + str(os.environ.get('PORT', '5000')) + '''</p>
                <p><strong>Ambiente:</strong> ''' + str(os.environ.get('FLASK_ENV', 'production')) + '''</p>
            </div>
            
            <div class="info">
                <h2>🔧 Configurações Detectadas:</h2>
                <p><strong>SESSION_SECRET:</strong> ''' + ('✅ Configurada' if os.environ.get('SESSION_SECRET') else '⚠️ Não configurada') + '''</p>
                <p><strong>DATABASE_URL:</strong> ''' + ('✅ Configurada' if os.environ.get('DATABASE_URL') else '⚠️ Não configurada') + '''</p>
            </div>
            
            <div class="info">
                <h2>🚀 Próximos Passos:</h2>
                <ol>
                    <li><strong>Configure as variáveis de ambiente no Railway:</strong>
                        <ul>
                            <li>SESSION_SECRET = (chave aleatória de 32+ caracteres)</li>
                            <li>DATABASE_URL = (URL do PostgreSQL)</li>
                            <li>FLASK_ENV = production</li>
                        </ul>
                    </li>
                    <li><strong>Ative o PostgreSQL no Railway</strong></li>
                    <li><strong>Volte para a aplicação completa (app.py)</strong></li>
                </ol>
            </div>
            
            <div class="info">
                <h2>✅ Status Railway:</h2>
                <p><span class="success">SUCESSO!</span> A aplicação está funcionando no Railway.</p>
                <p>O erro "Application failed to respond" foi resolvido.</p>
                <p>Agora podemos configurar o banco de dados e voltar para a aplicação completa.</p>
            </div>
            
            <hr>
            <p><em>🚂 SAMAPE versão ultra-simples para teste Railway</em></p>
            <p><em>Request ID que estava falhando: MLmyuEaxTsSDjcBVO8K9hQ</em></p>
        </div>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    """Endpoint de saúde para Railway"""
    return {
        'status': 'healthy',
        'service': 'samape',
        'environment': os.environ.get('FLASK_ENV', 'production'),
        'port': os.environ.get('PORT', '5000'),
        'message': 'Application is responding correctly'
    }

@app.route('/test')
def test():
    """Endpoint de teste simples"""
    return "OK - SAMAPE Railway Test Successful"

if __name__ == '__main__':
    # Configuração Railway
    port = int(os.environ.get('PORT', 5000))
    
    print("🚂 SAMAPE Railway Ultra-Simple Starting...")
    print(f"   Port: {port}")
    print(f"   Environment: {os.environ.get('FLASK_ENV', 'production')}")
    print("   URL: https://samape-py-samapedev.up.railway.app/")
    
    # Executar aplicação
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
