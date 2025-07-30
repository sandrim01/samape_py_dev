# SAMAPE - Sistema de Gestão de Serviços

Sistema de gestão desenvolvido em Flask para controle de ordens de serviço, clientes, equipamentos, estoque e financeiro.

## 🚀 Funcionalidades

- **Gestão de Clientes**: Cadastro e controle de clientes
- **Gestão de Equipamentos**: Controle de equipamentos e maquinários
- **Ordens de Serviço**: Criação e acompanhamento de OS
- **Controle Financeiro**: Entradas e saídas financeiras
- **Gestão de Estoque**: Controle de EPIs, ferramentas e peças
- **Gestão de Fornecedores**: Cadastro e pedidos para fornecedores
- **Relatórios**: Exportação de dados e notas fiscais
- **Controle de Frota**: Gestão de veículos e manutenções

## 🔧 Tecnologias

- **Backend**: Python 3.11+, Flask
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS, Bootstrap, JavaScript
- **ORM**: SQLAlchemy
- **Auth**: Flask-Login
- **Forms**: WTForms

## 📋 Pré-requisitos

- Python 3.11 ou superior
- PostgreSQL
- pip (gerenciador de pacotes Python)

## 🛠️ Instalação

1. **Clone o repositório**
```bash
git clone <url-do-repositorio>
cd samape_py_dev
```

2. **Crie um ambiente virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente**
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

5. **Configure o banco de dados**
```bash
# Crie um banco PostgreSQL
# Configure a URL no arquivo .env

# Execute as migrações
python migrate_db.py
```

6. **Execute a aplicação**
```bash
python main.py
```

## ⚙️ Configuração

### Variáveis de Ambiente

Edite o arquivo `.env` com as seguintes configurações:

```env
DATABASE_URL=postgresql://user:password@host:port/database
SESSION_SECRET=sua-chave-secreta-aqui
FLASK_ENV=development
ADMIN_DEFAULT_PASSWORD=admin123
```

### Primeira Execução

1. Execute `python migrate_db.py` para criar as tabelas
2. Acesse `http://localhost:5000`
3. Faça login com:
   - **Usuário**: admin
   - **Senha**: admin123 (ou a definida em ADMIN_DEFAULT_PASSWORD)
4. **IMPORTANTE**: Altere a senha padrão no primeiro login!

## 🔐 Segurança

### Medidas Implementadas

- ✅ CSRF Protection habilitado
- ✅ Senhas com hash seguro (Werkzeug)
- ✅ Rate limiting para login
- ✅ Validação de uploads de arquivo
- ✅ Proteção contra SQL Injection (SQLAlchemy ORM)
- ✅ Logging de auditoria

### Recomendações

- Sempre use HTTPS em produção
- Configure um SESSION_SECRET forte
- Mantenha as dependências atualizadas
- Faça backups regulares do banco
- Configure logs em produção

## 📁 Estrutura do Projeto

```
samape_py_dev/
├── app.py              # Configuração principal da aplicação
├── database.py         # Configuração do SQLAlchemy
├── models.py           # Modelos do banco de dados
├── routes.py           # Rotas da aplicação
├── forms.py            # Formulários WTForms
├── utils.py            # Funções utilitárias
├── jinja_filters.py    # Filtros personalizados do Jinja
├── logging_config.py   # Configuração de logging
├── error_handlers.py   # Tratamento de erros
├── static/             # Arquivos estáticos (CSS, JS, imagens)
├── templates/          # Templates HTML
└── logs/               # Arquivos de log (criado automaticamente)
```

## 🐛 Troubleshooting

### Problemas Comuns

1. **Erro de conexão com banco**
   - Verifique se o PostgreSQL está rodando
   - Confirme a DATABASE_URL no .env

2. **Erro de CSRF Token**
   - Certifique-se que o SESSION_SECRET está configurado
   - Limpe o cache do navegador

3. **Erro de permissões**
   - Verifique se o usuário do banco tem permissões
   - Confirme se as pastas de upload têm permissão de escrita

## 📝 Changelog

### Versão Atual
- ✅ Correções de segurança (CSRF, credenciais)
- ✅ Refatoração de importações circulares
- ✅ Implementação de logging adequado
- ✅ Melhor tratamento de exceções
- ✅ Documentação atualizada

### Próximas Melhorias
- [ ] Testes unitários
- [ ] API REST
- [ ] Interface mobile
- [ ] Relatórios avançados

## 👥 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto é propriedade privada. Todos os direitos reservados.

## 📞 Suporte

Para suporte técnico, entre em contato com a equipe de desenvolvimento.
