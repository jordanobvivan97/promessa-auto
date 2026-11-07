# Instruções do agente gerador (lote diário)

Este arquivo é o roteiro que o Claude segue toda noite, na tarefa agendada, para montar o lote de posts do dia seguinte. Ele escreve e renderiza; quem publica é o GitHub Actions (`scripts/publicar.py`).

## 1. Ler o estado

1. `marca.json`: horários, modo de aprovação e se o link da bio já está ativo.
2. `metricas/freio.json` (se existir): o campo `posts_por_dia` manda no volume. Sem o arquivo, use `posts_por_dia` de `marca.json`.
3. `metricas/posts.csv` (se existir): o que salvou e foi enviado mais. Só tire conclusão com 10 ou mais posts do mesmo tipo; abaixo disso, diga que a amostra é pequena e não mude a estratégia.
4. `pautas/banco.json` e as pastas `fila/` e `publicados/` dos últimos 30 dias, para não repetir pauta, abertura nem estrutura.
5. Os ebooks do projeto Promessa, para tirar o conteúdo da fonte. Nada de inventar dado, estudo ou estatística que não esteja neles.

## 2. Montar o lote de amanhã

- Quantidade: `posts_por_dia`. Horários: os primeiros N de `marca.json`; se N for maior que a lista, distribua entre 08h e 21h com pelo menos 2h30 de intervalo.
- Mistura padrão com 3 posts: 2 carrosséis e 1 estático. Com 4 ou 5: no máximo 1 estático a cada 2 carrosséis.
- Nunca dois posts do mesmo ebook no mesmo dia. Nunca o mesmo tema visual (`papel`, `cafe`, `rose`) em posts seguidos.
- Varie a abertura: carta, pergunta direta, cena curta (história em terceira pessoa), contraste "isso x aquilo", lista prática. Não repita o mesmo tipo de abertura no mesmo dia.
- Carrossel: 5 a 8 slides. Slide 1 é `capa`; o último é `fechamento` com um pedido de ação (salvar, enviar para alguém, comentar). Um slide, uma ideia.
- Estático: um slide `frase`, até cerca de 25 palavras.
- Legenda: 3 a 6 linhas curtas, uma pergunta ou convite, no máximo 5 hashtags.
- CTA de "link na bio" só quando `link_bio_ativo` for `true`.

## 3. Regras de escrita (não negociáveis)

- Português do Brasil, frases curtas e naturais. Sem travessão (o validador recusa). Sem jargão de coach ou psicologia pop.
- Falar com a mulher de 40+ como quem entende, nunca como quem julga. Sem culpa.
- Não prometer resultado terapêutico nem dar diagnóstico.
- Tema que toque violência, abuso, ameaça ou risco à vida: tratar com cuidado e incluir na legenda "Ligue 180" e, se couber, "CVV 188".
- Se uma pauta nova for criada, registrar no `pautas/banco.json` com o próximo id.

## 4. Produzir e conferir

Para cada post, criar `fila/AAAA-MM-DD/NN/post.json` no formato dos exemplos já publicados e rodar:

```
python scripts/validar.py fila/AAAA-MM-DD
python scripts/render.py fila/AAAA-MM-DD/*
```

Abrir todas as imagens geradas e conferir: texto inteiro visível, sem corte, legível no celular, sem erro de português. Corrigir e renderizar de novo se precisar.

## 5. Entregar

- `modo_aprovacao: "pr"`: criar a branch `lote-AAAA-MM-DD`, commitar e abrir um Pull Request com o título "Lote AAAA-MM-DD" e, na descrição, uma linha por post (horário, tipo, tema). Jordano aprova fazendo merge. Sem merge até o horário, o post não sai.
- `modo_aprovacao: "direto"`: commitar direto na branch principal.

Terminar com um resumo de 3 linhas: quantos posts, de quais pautas, e qualquer alerta (freio mudou o volume, pauta do banco acabando, erro de validação que exigiu reescrita).
