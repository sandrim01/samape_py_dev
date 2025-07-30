# Configuração SAMAPE para Railway

## 🚂 Deploy no Railway - Passo a Passo

### 1. Variáveis de Ambiente Obrigatórias

Configure estas variáveis no painel do Railway:

```bash
SESSION_SECRET=sua_chave_secreta_de_32_caracteres_aqui
DATABASE_URL=postgresql://user:password@host:port/database
FLASK_ENV=production
PORT=5000
```

### 2. Configuração do PostgreSQL

- Ative o PostgreSQL no Railway
- Copie a DATABASE_URL gerada automaticamente
- Cole na variável de ambiente DATABASE_URL

### 3. Deploy da Aplicação

1. **Push para GitHub** (já feito):
   ```bash
   git add .
   git commit -m "Railway deployment configuration"
   git push origin main
   ```

2. **Conectar no Railway**:
   - Vá para https://railway.app/
   - Conecte sua conta GitHub
   - Selecione o repositório samape_py_dev
   - Deploy automático iniciará

3. **Configurar Variáveis**:
   - No painel Railway, vá em "Variables"
   - Adicione as variáveis listadas acima

### 4. Comandos de Build (automático)

O Railway executará automaticamente:
```bash
pip install -r requirements.txt
python app.py
```

### 5. Inicialização do Banco

Após o deploy, execute uma vez:
```bash
python init_railway.py
```

### 6. Credenciais de Acesso

- **URL**: https://samape-py-samapedev.up.railway.app/
- **Usuário**: admin
- **Senha**: admin123

---

## 🔍 Solução de Problemas

### Erro: Application failed to respond

**Causa**: Variáveis de ambiente não configuradas

**Solução**:
1. Verifique se SESSION_SECRET está definida
2. Verifique se DATABASE_URL está correta
3. Confirme se PostgreSQL está ativo

### Erro: No module named 'psycopg2'

**Causa**: Dependência não instalada

**Solução**: Certifique-se que requirements.txt contém:
```
psycopg2-binary==2.9.9
```

### Erro: relation "user" does not exist

**Causa**: Banco não inicializado

**Solução**: Execute `python init_railway.py` no console do Railway

### Site não carrega / 404

**Causa**: Aplicação não está executando na porta correta

**Solução**: 
1. Verifique se PORT=5000 está definida
2. Confirme que app.py usa host='0.0.0.0'

---

## 📝 Estrutura de Arquivos Necessários

```
samape_py_dev/
├── app.py              # ✅ Configurado para Railway
├── Procfile            # ✅ Criado
├── requirements.txt    # ✅ Atualizado
├── config.py           # ✅ Configuração de ambiente
├── models.py          # ✅ Modelos do banco
├── routes.py          # ✅ Rotas da aplicação
├── init_railway.py    # ✅ Inicialização do banco
└── railway_diagnostic.py  # ✅ Script de diagnóstico
```

---

## 🎯 Checklist Final

- [ ] PostgreSQL ativo no Railway
- [ ] Variáveis de ambiente configuradas
- [ ] Deploy realizado com sucesso
- [ ] Banco inicializado (init_railway.py)
- [ ] Site acessível em https://samape-py-samapedev.up.railway.app/
- [ ] Login admin funcionando

---

## 📞 Comandos Úteis

### Verificar logs do Railway:
```bash
railway logs
```

### Executar comando no Railway:
```bash
railway run python init_railway.py
```

### Verificar status:
```bash
railway status
```

### Diagnosticar problemas:
```bash
python railway_diagnostic.py
```
