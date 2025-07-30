# CREDENCIAIS DE ACESSO - SAMAPE

## 🔐 USUÁRIO ADMINISTRADOR PADRÃO

### Opção 1 - Credenciais Principais:
- **Usuário:** admin
- **Senha:** admin123
- **Email:** admin@samape.local

### Opção 2 - Credenciais Alternativas:
- **Usuário:** Alessandro_jr  
- **Senha:** admin123
- **Email:** alessandro_jr@example.com

### Opção 3 - Credenciais de Backup:
- **Usuário:** samape_admin
- **Senha:** admin123
- **Email:** admin@samape.com

## 🌐 COMO ACESSAR:

1. **Iniciar a aplicação:**
   ```
   python app.py
   ```

2. **Acessar no navegador:**
   ```
   http://localhost:5000
   ```

3. **Página de login:**
   ```
   http://localhost:5000/login
   ```

4. **Usar uma das credenciais acima**

## ⚠️ IMPORTANTE:

- **ALTERE A SENHA** após o primeiro login
- Essas são credenciais de desenvolvimento
- Em produção, use credenciais mais seguras
- O sistema criará automaticamente um admin se não existir

## 🛠️ SOLUÇÃO DE PROBLEMAS:

Se não conseguir acessar:

1. Execute o script: `python setup_admin.py`
2. Verifique o arquivo de log da aplicação
3. Certifique-se de que o banco foi criado
4. Tente resetar o banco executando: `python migrate_db.py`

## 📋 VERIFICAÇÃO:

Para verificar se o usuário foi criado:
1. Acesse o banco SQLite
2. Execute: `SELECT * FROM user WHERE role = 'admin';`
3. Ou execute: `python setup_admin.py`
