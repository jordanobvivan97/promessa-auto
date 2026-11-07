# Agente de posts do Promessa

Gera e publica sozinho carrosséis e estáticos no Instagram do Promessa Não Sustenta Relacionamento.

## Como funciona

1. **Toda noite (Claude, tarefa agendada):** lê `GERAR.md`, escreve o lote do dia seguinte a partir dos 5 ebooks, renderiza as imagens com `scripts/render.py`, confere tudo com `scripts/validar.py` e abre um Pull Request.
2. **Você aprova (primeira semana):** abre o PR no app do GitHub, olha as imagens e faz merge. Sem merge, nada sai.
3. **Nos horários (GitHub Actions):** `scripts/publicar.py` publica pela API oficial do Instagram e move o post para `publicados/`.
4. **Todo dia de manhã:** `scripts/metricas.py` coleta alcance, salvamentos e envios e atualiza o freio de volume em `metricas/freio.json`.
5. **A cada 10 dias:** o token do Instagram é renovado sozinho.

Botão de emergência: crie um arquivo chamado `PAUSADO` na raiz do repositório e nada mais é publicado até você apagá-lo.

Custo: zero. GitHub Actions e jsDelivr são gratuitos para repositório público; a API do Instagram não cobra.

## Configuração (uma vez só, cerca de 30 minutos)

### 1. Conta do Instagram
A conta precisa ser profissional (Criador ou Empresa). No app: Configurações, Tipo de conta e ferramentas, Mudar para conta profissional.

### 2. App na Meta
1. Entre em developers.facebook.com com seu Facebook e crie uma conta de desenvolvedor, se ainda não tiver.
2. Meus apps, Criar app. Escolha o caso de uso "Gerenciar mensagens e conteúdo no Instagram".
3. No painel do app, em Permissões e recursos, adicione `instagram_business_basic`, `instagram_business_content_publish` e `instagram_business_manage_insights`.
4. Em Funções do app, Testadores do Instagram, convide o usuário do Promessa. Depois aceite o convite no Instagram (Configurações, Apps e sites, Convites de testador).
5. Volte em "Configuração da API com login do Instagram", clique em Adicionar conta, entre com a conta do Promessa e clique em Gerar token. Copie o token na hora: ele aparece uma vez só e começa com `IGAA`.
6. Para descobrir o ID da conta, abra no navegador (trocando SEU_TOKEN):
   `https://graph.instagram.com/me?fields=user_id,username&access_token=SEU_TOKEN`
   O número em `user_id` é o seu IG_USER_ID.

Publicar na sua própria conta funciona com acesso padrão, sem revisão do app pela Meta.

### 3. Repositório no GitHub
1. Crie um repositório **público** chamado `promessa-auto` na conta jordanobvivan97. Ele precisa ser público porque o Instagram baixa as imagens por um link aberto; tokens ficam em Secrets, que são criptografados e nunca aparecem no código. Os ebooks não vão para o repositório.
2. Em Settings, Secrets and variables, Actions, crie:
   - `IG_TOKEN`: o token do passo 2.5
   - `IG_USER_ID`: o número do passo 2.6
   - `GH_PAT`: um token do GitHub (Settings da sua conta, Developer settings, Fine-grained tokens) com acesso só a este repositório e permissão de leitura e escrita em Secrets. Serve para renovar o token do Instagram sozinho.
3. Em Settings, Actions, General, marque "Read and write permissions".

Você nunca precisa me passar esses tokens: eles vão direto para os Secrets do GitHub.

## Estrutura

```
marca.json            horários, volume, modo de aprovação, regras do freio
GERAR.md              roteiro que o Claude segue para montar cada lote
pautas/banco.json     50 pautas extraídas dos ebooks
fila/AAAA-MM-DD/NN/   posts aprovados esperando o horário (post.json + slides)
publicados/           o que já foi ao ar, com link
metricas/             posts.csv e freio.json
scripts/              render, validar, publicar, metricas
```

## Depois da primeira semana

Se os lotes estiverem saindo bons, troque `"modo_aprovacao": "pr"` por `"direto"` em `marca.json` e a aprovação deixa de ser necessária. O freio continua ligado: se o alcance mediano por post cair 30% ou mais numa janela de 14 dias, o volume desce 1 post por dia; com duas janelas estáveis, sobe 1, até o máximo de 5.
