# Como atualizar o site "Séries do Murilo"

Pasta: `/workspace/site-series/`

| Arquivo | Para quê |
|---|---|
| `data.json` | Dados de todas as seções (fonte do site) |
| `parse_resumo.py` | Converte o resumo diário de séries (`resumo-AAAA-MM-DD-series.md`) e o de filmes (`resumo-AAAA-MM-DD-filmes.md`) em `data.json` |
| `build.py` | Lê `data.json` e gera `index.html` (CSS inline, sem JS) |
| `index.html` | A página publicada |
| `preview-*.png` | Capturas de conferência: celular escuro (página inteira), celular na seção Filmes, celular claro e desktop. Não precisam ir para o repositório |

Regra de ouro: o texto vem **sempre** do resumo/novidades, copiado literalmente. Nada de reescrever ou inventar.

## 1. Todo dia às 8h (resumo novo)

Depois que o resumo das 8h for gravado em `/workspace/avisos-series/resumo-AAAA-MM-DD-series.md` e `…-filmes.md`:

```bash
cd /workspace/site-series
D=$(date +%F)
python3 parse_resumo.py ../avisos-series/resumo-$D-series.md \
  --filmes ../avisos-series/resumo-$D-filmes.md -o data.json
python3 build.py            # data.json -> index.html
```

- Sem `--filmes`, o script procura sozinho o `resumo-AAAA-MM-DD-filmes.md` ao lado do resumo de séries. Se não achar, avisa e gera o site sem a seção Filmes. Use `--sem-filmes` para omitir de propósito.

- O `parse_resumo.py` lê as seis seções na ordem canônica: 🎬 Lançamentos de hoje, 🆕 Novidades de streaming no Brasil (+ Ainda sem data no Brasil), ⏳ Ativas atrasadas, 📺 Episódio recente, 📅 Episódio de hoje e ⏳ Finalizadas atrasadas.
- Grava `atualizado_em` com a hora atual de Brasília. Essa é a hora que aparece em "Atualizado em …".
- A seção 🎞️ Filmes (`secoes.filmes` no data.json) é sempre a última.
- Se o formato do resumo mudar (por exemplo, uma linha que não segue `x/y · próximo: …`), o script **para com erro** e mostra a linha problemática. Ele nunca adivinha.

### Novidades que entraram depois do resumo
Se alguma novidade foi acrescentada em `novidades.md` **já no formato do resumo**
(`[🆕|🧊|✏️ ]DD/MM[/AAAA] (dia) - Nome - Tn - info`), passe também `--extra`:

```bash
python3 parse_resumo.py ../avisos-series/resumo-$(date +%F)-series.md \
  --extra ../avisos-series/novidades.md -o data.json
```

Só entram as linhas que ainda não estão no resumo (comparação por nome + temporada), e a lista é reordenada por data.
Foi assim que a linha 🆕 13/01/2027 de *Seu Amigão da Vizinhança: Homem-Aranha* (T2) entrou no data.json de 09/10.
As linhas no formato `- Nome | … | … ` do `novidades.md` são anotações internas e são ignoradas.

### Formato aceito do resumo de filmes (parsing estrito)

```
**🎞️ Filmes**

**Título pt-BR (Título original, AAAA)**
🏷️ **Tipo de lançamento:** texto
🎟️ **Cinema no Brasil:** texto
🛒 **Aluguel e compra:** [texto na mesma linha, OU uma linha por loja abaixo]
Loja: texto
📺 **Streaming:** [texto, OU uma linha por plataforma abaixo]
Plataforma: texto
ℹ️ nota (pode aparecer depois de qualquer campo; fica presa ao campo anterior)
__________
(próximo filme)
```

Os quatro campos são obrigatórios em cada filme. Um campo desconhecido ou repetido, uma linha solta fora de Aluguel/Streaming ou um título sem `(Original, ano)` faz o script **parar com erro**.
No `data.json`, cada filme tem `titulo`, `titulo_original` e `ano`. Os campos `tipo_lancamento`, `cinema_brasil`, `aluguel_compra` e `streaming` trazem `emoji`, `rotulo`, `valor` (texto da mesma linha ou `null`) e `notas` (ℹ️). Os dois últimos também trazem `linhas` (`[{loja, texto}]`, com `loja: null` quando a linha não tem "Loja:").
O `filmes.md` é a base de pesquisa (com fontes), não entra no site; o site usa só o resumo de filmes do dia.

## 2. Depois de marcar um episódio

O jeito mais seguro é o mesmo fluxo: regenerar o resumo de séries do dia (o mesmo texto usado no Google Doc "Resumo de Séries ao vivo"), salvar em um `.md` e rodar `parse_resumo.py` + `build.py`.

Se for só um ajuste rápido, edite o `data.json` à mão e rode `python3 build.py`. Na série marcada:

1. `progresso.texto`, `progresso.vistos` e `progresso.total`: ex. `"9/21"` → `"10/21"`, `vistos: 10`. A barra é calculada a partir de vistos/total.
2. `proximo`: `texto` (linha completa, ex. `"1x11 - EN / PT"`), `codigo`, `titulo_en` e `titulo_pt`, com os mesmos textos do resumo/nomes-ptbr.
3. `status` (`🟢`/`🔴`), `brasil` e `notas`, se mudarem.
4. Se a série saiu da seção (ex. ficou em dia), apague o objeto da lista `itens`.
5. Atualize `atualizado_em` (ISO, ex. `"2026-10-09T21:30-03:00"`), ou apague o campo, que aí o build usa a hora atual.

Campos de cada série (seções de séries):

```json
{
  "nome": "Coven Academy", "nome_original": null, "status": "🟢",
  "progresso": {"texto": "9/21", "vistos": 9, "total": 21},
  "proximo": {"rotulo": "próximo", "codigo": "1x10", "titulo_en": "Time Warp",
              "titulo_pt": "Distorção Temporal", "texto": "1x10 - Time Warp / Distorção Temporal"},
  "transmissao": "(opcional, linha 📡)", "brasil": "T1 completa no Disney+",
  "notas": ["2ª temporada não anunciada (nem renovada, nem cancelada)"]
}
```

Lançamentos têm `episodios` (ex. `"13x07 e 13x08"`) e `titulo_pt_nota` (linha 📺) no lugar de `proximo`.
Novidades têm `selo` (🆕/🧊/✏️ ou vazio), `data`, `dia_semana`, `nome`, `temporada`, `info` e `texto`.

## 3. Conferir antes de publicar

O site segue o tema do aparelho: escuro suave (`#1c1f26`) ou claro creme (`#f7f4ee`), via `prefers-color-scheme`. As cores ficam no bloco `CSS` do `build.py`: variáveis `--c-<seção>`, uma versão para o escuro e outra para o claro.

```bash
# escuro (preferredColorScheme=0) / claro (=1); a janela alta pega a página inteira
# (o Chrome deixa um fundo vazio no fim: dá para cortar com PIL)
google-chrome --headless=new --no-sandbox --hide-scrollbars --blink-settings=preferredColorScheme=0 \
  --window-size=390,16000 --screenshot=preview-mobile.png file://$PWD/index.html
google-chrome --headless=new --no-sandbox --hide-scrollbars --blink-settings=preferredColorScheme=0 \
  --window-size=1280,8000 --screenshot=preview-desktop.png file://$PWD/index.html
```

Atenção: sem `--blink-settings=preferredColorScheme=0`, o Chrome headless renderiza no modo **claro**.

## 4. Publicar no GitHub Pages (repositório ainda não criado)

Configuração (uma vez só):
1. Criar o repositório no GitHub (ex. `series`). No plano gratuito o Pages exige repositório **público**. O `noindex` evita buscadores, mas qualquer pessoa com o link consegue abrir.
2. Na pasta: `git init && git branch -M main`, criar um `.gitignore` com `preview-*.png`, depois `git add index.html data.json build.py parse_resumo.py COMO-ATUALIZAR.md .gitignore && git commit -m "site inicial"`.
3. `git remote add origin git@github.com:<usuario>/<repo>.git && git push -u origin main`.
4. No GitHub: Settings → Pages → Source: *Deploy from a branch* → `main` / `(root)`. O endereço fica `https://<usuario>.github.io/<repo>/`.

A cada atualização (8h e após marcar episódio):

```bash
cd /workspace/site-series
python3 parse_resumo.py ../avisos-series/resumo-$(date +%F)-series.md -o data.json   # ou edição manual
python3 build.py
git add index.html data.json && git commit -m "Atualiza séries $(date '+%d/%m %Hh%M')" && git push
```

O Pages leva cerca de 1 minuto para refletir o push.
