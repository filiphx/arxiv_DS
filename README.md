# arXiv → Telegram — Sistemas Dinâmicos

Bot que roda via **GitHub Actions** e envia os artigos novos do arXiv
(categoria `math.DS`) para o seu Telegram todo dia de manhã.

---

## Setup em 5 minutos

### 1. Criar o bot no Telegram

1. Abra o Telegram e fale com **@BotFather**
2. Mande `/newbot`, escolha um nome e um username (ex: `meu_arxiv_bot`)
3. Copie o **token** que ele te devolve (formato `123456:ABC-DEF...`)

### 2. Descobrir seu Chat ID

1. Inicie uma conversa com o bot que você criou (mande qualquer mensagem)
2. Abra no browser:
   ```
   https://api.telegram.org/bot<SEU_TOKEN>/getUpdates
   ```
3. No JSON retornado, copie o valor de `result[0].message.chat.id`
   (pode ser positivo para conta pessoal ou negativo para grupo)

> **Dica:** para receber num grupo, adicione o bot ao grupo e mande uma
> mensagem lá. O `chat.id` do grupo aparecerá no `getUpdates`.

### 3. Criar o repositório no GitHub

```bash
git init arxiv-bot
cd arxiv-bot
# copie os dois arquivos para cá:
#   arxiv_telegram.py
#   .github/workflows/arxiv_notify.yml
git add .
git commit -m "chore: arxiv telegram bot"
gh repo create arxiv-bot --public --push  # ou crie pelo site e dê push
```

### 4. Adicionar os Secrets no GitHub

No repositório → **Settings → Secrets and variables → Actions → New repository secret**

| Nome              | Valor                        |
|-------------------|------------------------------|
| `TELEGRAM_TOKEN`  | Token do BotFather           |
| `TELEGRAM_CHAT_ID`| Seu chat.id (número inteiro) |

### 5. Testar

Vá em **Actions → arXiv → Telegram → Run workflow** e dispare manualmente.
Se tudo estiver certo, você receberá as mensagens no Telegram em segundos.

---

## Personalização

| O que mudar | Onde |
|-------------|------|
| Categorias do arXiv | `CATEGORIES` no topo de `arxiv_telegram.py` |
| Horário de envio | `cron` em `.github/workflows/arxiv_notify.yml` |
| Número máximo de artigos | `MAX_RESULTS` em `arxiv_telegram.py` |
| Filtrar por palavra-chave | Adicione lógica no loop `for entry in entries` |

### Categorias úteis

| Categoria | Descrição |
|-----------|-----------|
| `math.DS` | Dynamical Systems |
| `math.CA` | Classical Analysis and ODEs |
| `nlin.CD` | Chaotic Dynamics |
| `math-ph` | Mathematical Physics |
| `math.PR` | Probability Theory |

### Horários cron úteis (UTC)

| Cron | Hora BRT |
|------|----------|
| `0 8 * * 1-5` | 05:00, dias úteis |
| `0 11 * * *`  | 08:00, todo dia |
| `0 14 * * *`  | 11:00, todo dia |

---

## Dependências

Zero — só Python 3.8+ stdlib. Sem `pip install` necessário.
