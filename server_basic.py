#!/usr/bin/env python3
"""
Servidor HTTP básico sem Flask - para testar se Railway funciona
"""

import os
import http.server
import socketserver
from urllib.parse import urlparse

class SAMAPEHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>SAMAPE Railway - Teste Básico</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial; margin: 20px; background: #f0f8ff; }}
                    .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                    .success {{ color: #28a745; font-size: 24px; }}
                    .info {{ background: #e3f2fd; padding: 15px; margin: 10px 0; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="success">🎉 SAMAPE Railway - SERVIDOR BÁSICO FUNCIONANDO!</h1>
                    
                    <div class="info">
                        <h2>📊 Status do Servidor:</h2>
                        <p><strong>Status:</strong> ✅ Online e Respondendo</p>
                        <p><strong>Tipo:</strong> Python HTTP Server (sem Flask)</p>
                        <p><strong>Porta:</strong> {os.environ.get('PORT', '5000')}</p>
                        <p><strong>Ambiente:</strong> {os.environ.get('FLASK_ENV', 'Railway')}</p>
                    </div>
                    
                    <div class="info">
                        <h2>🔍 Diagnóstico:</h2>
                        <p><strong>✅ SUCESSO!</strong> Railway conseguiu executar Python básico.</p>
                        <p>Se você está vendo esta página, significa que:</p>
                        <ul>
                            <li>✅ Railway está funcionando</li>
                            <li>✅ Python está funcionando</li>
                            <li>✅ Porta está configurada corretamente</li>
                            <li>✅ Deploy foi bem-sucedido</li>
                        </ul>
                    </div>
                    
                    <div class="info">
                        <h2>🚀 Próximos Passos:</h2>
                        <ol>
                            <li><strong>Agora sabemos que Railway funciona!</strong></li>
                            <li><strong>O problema anterior era nas dependências (Flask, etc.)</strong></li>
                            <li><strong>Vamos voltar gradualmente para Flask:</strong>
                                <ul>
                                    <li>Primeiro: Flask puro</li>
                                    <li>Depois: Adicionar SQLAlchemy</li>
                                    <li>Por último: Aplicação completa</li>
                                </ul>
                            </li>
                        </ol>
                    </div>
                    
                    <div class="info">
                        <h2>📋 Variáveis de Ambiente:</h2>
                        <p><strong>PORT:</strong> {os.environ.get('PORT', 'Não definida')}</p>
                        <p><strong>SESSION_SECRET:</strong> {'Definida' if os.environ.get('SESSION_SECRET') else 'Não definida'}</p>
                        <p><strong>DATABASE_URL:</strong> {'Definida' if os.environ.get('DATABASE_URL') else 'Não definida'}</p>
                        <p><strong>FLASK_ENV:</strong> {os.environ.get('FLASK_ENV', 'Não definida')}</p>
                    </div>
                    
                    <hr>
                    <p><em>🐍 Servidor Python HTTP básico - Teste Railway</em></p>
                    <p><em>Problema "Application failed to respond" identificado!</em></p>
                </div>
            </body>
            </html>
            """
            
            self.wfile.write(html_content.encode('utf-8'))
            
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = '{"status": "ok", "server": "python-basic", "message": "Railway working"}'
            self.wfile.write(response.encode('utf-8'))
            
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<h1>404 - Not Found</h1><p>Apenas / e /health estao disponiveis</p>")

def main():
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🐍 Iniciando servidor Python básico na porta {port}")
    print(f"🌐 URL: https://samape-py-samapedev.up.railway.app/")
    print("📊 Testando se Railway consegue executar Python...")
    
    with socketserver.TCPServer(("0.0.0.0", port), SAMAPEHandler) as httpd:
        print(f"✅ Servidor rodando em 0.0.0.0:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
