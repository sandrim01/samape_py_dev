# 🚂 CONFIGURAR RAILWAY - PASSO A PASSO

## 🎯 PARA RESOLVER ERRO 502

### 1. ACESSE O RAILWAY
- URL: https://railway.app/
- Faça login na sua conta
- Procure pelo projeto `samape_py_dev`

### 2. CONFIGURE VARIÁVEIS DE AMBIENTE

No projeto, clique em **"Variables"** e adicione:

#### ✅ Variáveis Obrigatórias:

```bash
SESSION_SECRET
Valor: P8kM2nQ5rX9vB3cF7hL4sW1uY6eT0iO2vX8qR4tW6yE3uI5oB1s

DATABASE_URL  
Valor: postgresql://postgres:fzsZiDkvLIsSlVGzrOyEbgWTStUvfsQA@centerbeam.proxy.rlwy.net:51097/railway

FLASK_ENV
Valor: production

PORT
Valor: 5000
```

### 3. VERIFICAR POSTGRESQL

#### Se PostgreSQL não estiver ativo:
1. No Railway, clique **"+ New"**
2. Selecione **"Database"**
3. Escolha **"PostgreSQL"**
4. Aguarde criação (1-2 minutos)
5. A `DATABASE_URL` será gerada automaticamente
6. **Substitua** a DATABASE_URL acima pela nova gerada

### 4. AGUARDAR REDEPLOY

- Após salvar as variáveis, Railway fará redeploy automático
- Aguarde 2-3 minutos
- Acesse: https://samape-py-samapedev.up.railway.app/

### 5. VERIFICAR DIAGNÓSTICO

A página deve mostrar:
```
🚂 SAMAPE Railway - Diagnóstico
📊 Status da Aplicação: ✅ Aplicação inicializada
🗄️ Status do Banco PostgreSQL: ✅ FUNCIONANDO
```

Se mostrar "❌ ERRO", o problema é específico do banco.

## 🔧 SE BANCO CONTINUAR COM ERRO

### Opção 1: Recriar PostgreSQL
1. Delete o PostgreSQL atual no Railway
2. Crie um novo conforme passo 3 acima
3. Use a nova DATABASE_URL gerada

### Opção 2: Verificar Conectividade
- O host `centerbeam.proxy.rlwy.net` pode estar com problema
- Railway pode estar fazendo manutenção
- Aguarde 10-15 minutos e tente novamente

### Opção 3: Usar SQLite Temporário
Se quiser testar a aplicação sem PostgreSQL:
1. **Remova** a variável `DATABASE_URL` do Railway
2. A aplicação usará SQLite local temporariamente
3. Depois configure PostgreSQL normalmente

## ⏰ TIMELINE ESPERADO

- **Agora**: Configurando variáveis no Railway
- **2-3 min**: Redeploy automático
- **5 min**: Site funcionando com diagnóstico
- **Se banco OK**: Voltar para app.py completo
- **10 min**: SAMAPE 100% funcional

## 📞 INSTRUÇÕES ESPECÍFICAS

### Como Adicionar Variável no Railway:
1. Projeto > **Variables** (aba lateral)
2. Clique **"New Variable"**
3. **Name**: (nome da variável)
4. **Value**: (valor da variável)
5. Clique **"Add"**
6. Repita para todas as 4 variáveis

### Como Ativar PostgreSQL:
1. No projeto, clique **"+ New"** (botão roxo)
2. **Add a Service** > **Database**
3. **Add PostgreSQL**
4. Aguarde criação
5. PostgreSQL aparecerá como novo serviço
6. Nova `DATABASE_URL` será criada automaticamente

---

## 🎯 RESULTADO ESPERADO

Após configuração:
- ✅ Site carregando normalmente
- ✅ Banco PostgreSQL conectado
- ✅ Diagnóstico mostrando "TUDO OK"
- ✅ Pronto para voltar ao app.py completo

**O erro 502 deve desaparecer assim que as variáveis estiverem configuradas!**
