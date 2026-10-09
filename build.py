#!/usr/bin/env python3
"""Lê data.json e gera index.html (página única, CSS inline, sem JS).

Uso: python3 build.py [data.json] [index.html]
"""
import json, sys
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]

# (chave, rótulo curto do chip). Cores por seção ficam no CSS (.s-<âncora>), com versões clara/escura.
ORDEM = [
    ("lancamentos", "Lançamentos"),
    ("novidades", "Novidades"),
    ("ativas_atrasadas", "Ativas atrasadas"),
    ("episodio_recente", "Recentes"),
    ("episodio_hoje", "Hoje"),
    ("finalizadas_atrasadas", "Finalizadas"),
    ("filmes", "Filmes"),
]
ANCORA = {"lancamentos": "lancamentos", "novidades": "novidades", "ativas_atrasadas": "ativas",
          "episodio_recente": "recente", "episodio_hoje": "hoje", "finalizadas_atrasadas": "finalizadas",
          "filmes": "filmes"}

e = lambda s: escape(s or "", quote=True)


def fmt_data(dt):
    dt = dt.astimezone(TZ)
    return f"{DIAS[dt.weekday()]}, {dt.day} de {MESES[dt.month-1]} de {dt.year}, às {dt:%Hh%M} (Brasília)"


def barra(p):
    if not p or p.get("total") in (None, 0):
        return ""
    pct = max(0, min(100, round(100 * p["vistos"] / p["total"])))
    return (f'<div class="prog"><div class="bar" role="progressbar" aria-valuenow="{p["vistos"]}" '
            f'aria-valuemin="0" aria-valuemax="{p["total"]}"><span style="width:{pct}%"></span></div>'
            f'<span class="ptxt">{e(p["texto"])}</span></div>')


def nome_html(it):
    s = f'<h3 class="nm">{e(it["nome"])}'
    if it.get("status"):
        s += f' <span class="dot">{e(it["status"])}</span>'
    s += "</h3>"
    if it.get("nome_original"):
        s += f'<p class="orig">{e(it["nome_original"])}</p>'
    return s


def linhas_extra(it):
    out = ""
    if it.get("titulo_pt_nota"):
        out += f'<p class="ln"><span class="ic">📺</span><span>{e(it["titulo_pt_nota"])}</span></p>'
    if it.get("transmissao"):
        out += f'<p class="ln"><span class="ic">📡</span><span>{e(it["transmissao"])}</span></p>'
    if it.get("brasil"):
        out += f'<p class="ln br"><span class="ic">🇧🇷</span><span>{e(it["brasil"])}</span></p>'
    for n in it.get("notas", []):
        out += f'<p class="nota"><span class="ic">ℹ️</span><span>{e(n)}</span></p>'
    for n in it.get("outras_linhas", []):
        out += f'<p class="nota"><span>{e(n)}</span></p>'
    return out


def card_serie(it):
    ep = it["proximo"]
    if ep.get("titulo_en") is not None:
        tit = e(ep["titulo_en"])
        if ep.get("titulo_pt") is not None:
            tit += f' <span class="sl">/</span> <span class="pt">{e(ep["titulo_pt"])}</span>'
        ep_html = f'<b class="code">{e(ep["codigo"])}</b> <span class="sl">-</span> {tit}'
    else:
        ep_html = f'<b class="code">{e(ep["codigo"])}</b>'
    return (f'<article class="card">{nome_html(it)}{barra(it.get("progresso"))}'
            f'<p class="ep"><span class="lbl">{e(ep["rotulo"])}</span> {ep_html}</p>'
            f'{linhas_extra(it)}</article>')


def card_lancamento(it):
    return (f'<article class="card">{nome_html(it)}'
            f'<p class="ep"><span class="lbl">episódios</span> <b class="code">{e(it["episodios"])}</b></p>'
            f'{barra(it.get("progresso"))}{linhas_extra(it)}</article>')


def card_filme(f):
    h = (f'<article class="card filme"><h3 class="nm">{e(f["titulo"])}</h3>'
         f'<p class="orig">{e(f["titulo_original"])} · {e(f["ano"])}</p>')
    for key in ("tipo_lancamento", "cinema_brasil", "aluguel_compra", "streaming"):
        c = f.get(key)
        if not c:
            continue
        h += f'<div class="fld"><p class="flbl"><span class="ic">{e(c["emoji"])}</span>{e(c["rotulo"])}</p>'
        if c.get("valor"):
            h += f'<p class="fval">{e(c["valor"])}</p>'
        if c.get("linhas"):
            h += '<ul class="lojas">'
            for l in c["linhas"]:
                if l.get("loja"):
                    h += f'<li><b>{e(l["loja"])}:</b> {e(l["texto"])}</li>'
                else:
                    h += f'<li>{e(l["texto"])}</li>'
            h += "</ul>"
        for n in c.get("notas", []):
            h += f'<p class="nota"><span class="ic">ℹ️</span><span>{e(n)}</span></p>'
        h += "</div>"
    return h + "</article>"


def novidades_html(sec):
    li = []
    for n in sec["itens"]:
        selo = n.get("selo") or ""
        cls = {"🆕": "new", "🧊": "ice", "✏️": "edit"}.get(selo, "")
        badge = f'<span class="badge {cls}">{e(selo)}</span>' if selo else ""
        li.append(f'<li class="{cls}"><time>{e(n["data"])} <small>{e(n["dia_semana"])}</small></time>'
                  f'<div class="tl"><b>{e(n["nome"])}</b> <span class="tmp">{e(n["temporada"])}</span>{badge}'
                  f'<span class="inf">{e(n["info"])}</span></div></li>')
    out = f'<ol class="timeline">{"".join(li)}</ol>'
    sd = sec.get("sem_data")
    if sd and sd.get("itens"):
        rows = "".join(f'<li><b>{e(x["nome"])}</b> <span class="inf">{e(x["info"])}</span></li>' for x in sd["itens"])
        out += f'<h3 class="sub">🗓️ {e(sd["titulo"])}</h3><ul class="semdata">{rows}</ul>'
    return out


CSS = """
:root{
 --bg:#1c1f26;--bg2:#21252d;--card:#262a33;--line:#343945;--track:#3a3f4b;
 --txt:#e6e6e6;--txt2:#cfd2d8;--mut:#a3a8b3;--hdr:#232731;--navbg:rgba(28,31,38,.94);
 --c-lancamentos:#d29a96;--c-novidades:#93bfa0;--c-ativas:#d4b880;--c-recente:#93aad3;
 --c-hoje:#b4a0d4;--c-finalizadas:#86bdb5;--c-filmes:#d6ab8f;
 --new:#93bfa0;--ice:#93b9d3;--edit:#d4c080;
}
@media (prefers-color-scheme: light){:root{
 --bg:#f7f4ee;--bg2:#f2eee6;--card:#fffdf9;--line:#e3dccf;--track:#e8e1d4;
 --txt:#33363b;--txt2:#45484e;--mut:#6b6f76;--hdr:#efe9de;--navbg:rgba(247,244,238,.94);
 --c-lancamentos:#a85d58;--c-novidades:#4f8761;--c-ativas:#946f2a;--c-recente:#4a6ca3;
 --c-hoje:#7659a6;--c-finalizadas:#3d8279;--c-filmes:#9c6444;
 --new:#4f8761;--ice:#4a7fa3;--edit:#946f2a;
}}
.s-lancamentos{--c:var(--c-lancamentos)}.s-novidades{--c:var(--c-novidades)}.s-ativas{--c:var(--c-ativas)}
.s-recente{--c:var(--c-recente)}.s-hoje{--c:var(--c-hoje)}.s-finalizadas{--c:var(--c-finalizadas)}.s-filmes{--c:var(--c-filmes)}
*{box-sizing:border-box}
html{scroll-behavior:smooth;scroll-padding-top:72px;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--txt);font:17px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans",sans-serif,"Apple Color Emoji","Noto Color Emoji";
 -webkit-font-smoothing:antialiased}
header.top{padding:32px 20px 22px;background:var(--hdr);border-bottom:1px solid var(--line)}
header.top h1{margin:0;font-size:1.85rem;line-height:1.2;letter-spacing:-.01em;font-weight:750}
header.top h1 span{color:var(--c-lancamentos)}
header.top .sub1{margin:8px 0 0;color:var(--txt2);font-size:1rem}
header.top .upd{margin:4px 0 0;color:var(--mut);font-size:.85rem}
nav.chips{position:sticky;top:0;z-index:10;display:flex;gap:8px;overflow-x:auto;padding:12px 20px;
 background:var(--navbg);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);border-bottom:1px solid var(--line);scrollbar-width:none}
nav.chips::-webkit-scrollbar{display:none}
nav.chips a{flex:0 0 auto;text-decoration:none;color:var(--txt);font-size:.88rem;font-weight:600;line-height:1.3;padding:8px 14px;border-radius:999px;
 background:color-mix(in srgb,var(--c) 12%,var(--card));border:1px solid color-mix(in srgb,var(--c) 40%,var(--line));white-space:nowrap}
nav.chips a:hover,nav.chips a:focus-visible{background:color-mix(in srgb,var(--c) 22%,var(--card))}
nav.chips a .n{color:var(--mut);font-weight:500;margin-left:5px}
main{padding:4px 14px 44px;max-width:1200px;margin:0 auto}
section.sec{margin:26px 0 0;padding:20px 16px 18px;border-radius:20px;background:var(--bg2);
 border:1px solid var(--line);border-top:3px solid var(--c)}
section.sec>h2{margin:0 0 16px;font-size:1.3rem;line-height:1.3;font-weight:700;display:flex;align-items:center;gap:10px}
section.sec>h2 .cnt{margin-left:auto;font-size:.8rem;font-weight:700;color:var(--txt);background:color-mix(in srgb,var(--c) 22%,transparent);
 border:1px solid color-mix(in srgb,var(--c) 45%,transparent);border-radius:999px;padding:1px 11px}
.grid{display:grid;gap:14px;grid-template-columns:1fr}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:16px 16px 14px;min-width:0}
.card .nm{margin:0;font-size:1.1rem;font-weight:700;line-height:1.35}
.card .dot{font-size:.75rem;vertical-align:2px;margin-left:2px}
.card .orig{margin:2px 0 0;color:var(--mut);font-size:.88rem;font-style:italic}
.prog{display:flex;align-items:center;gap:12px;margin:12px 0 8px}
.bar{flex:1;height:6px;background:var(--track);border-radius:99px;overflow:hidden}
.bar span{display:block;height:100%;background:var(--c);opacity:.85;border-radius:99px;min-width:3px}
.ptxt{font-size:.85rem;font-variant-numeric:tabular-nums;color:var(--txt2);font-weight:600}
.ep{margin:8px 0 6px;font-size:.98rem;overflow-wrap:anywhere}
.ep .lbl{display:inline-block;font-size:.7rem;text-transform:uppercase;letter-spacing:.07em;color:var(--c);font-weight:700;margin-right:4px}
.ep .code{font-variant-numeric:tabular-nums;font-weight:700}
.ep .sl{color:var(--mut)}
.ep .pt{color:var(--txt2)}
.ln,.nota{display:flex;gap:8px;margin:7px 0 0;font-size:.93rem;color:var(--txt2);overflow-wrap:anywhere}
.ic{flex:0 0 auto;width:1.3em;text-align:center}
.nota{font-size:.84rem;color:var(--mut);line-height:1.55}
.filme .fld{margin-top:12px;padding-top:10px;border-top:1px solid var(--line)}
.filme .flbl{margin:0;display:flex;gap:8px;font-size:.74rem;text-transform:uppercase;letter-spacing:.07em;font-weight:700;color:var(--c)}
.filme .fval{margin:3px 0 0;padding-left:calc(1.3em + 8px);font-size:.95rem;color:var(--txt2);overflow-wrap:anywhere}
.filme .lojas{margin:4px 0 0;padding:0 0 0 calc(1.3em + 8px);list-style:none}
.filme .lojas li{margin:5px 0 0;font-size:.92rem;color:var(--txt2);overflow-wrap:anywhere}
.filme .lojas b{color:var(--txt);font-weight:650}
.timeline{list-style:none;margin:0;padding:0}
.timeline li{display:grid;grid-template-columns:80px 1fr;gap:8px;padding:11px 6px;border-bottom:1px solid var(--line);font-size:.95rem;border-radius:10px}
.timeline li:last-child{border-bottom:0}
.timeline time{font-weight:700;color:var(--c);font-variant-numeric:tabular-nums;font-size:.85rem;line-height:1.35;white-space:nowrap}
.timeline time small{display:block;color:var(--mut);font-weight:500}
.timeline .tl{min-width:0;overflow-wrap:anywhere}
.timeline .tmp{display:inline-block;font-size:.72rem;font-weight:700;padding:0 7px;border-radius:6px;background:var(--track);color:var(--txt2);margin-left:3px;vertical-align:1px}
.timeline .inf{display:block;color:var(--mut);font-size:.88rem;margin-top:2px}
.badge{display:inline-block;margin-left:6px;font-size:.72rem;padding:0 6px;border-radius:6px;border:1px solid var(--line);vertical-align:1px}
.badge.new{border-color:color-mix(in srgb,var(--new) 55%,transparent);background:color-mix(in srgb,var(--new) 14%,transparent)}
.badge.ice{border-color:color-mix(in srgb,var(--ice) 55%,transparent);background:color-mix(in srgb,var(--ice) 14%,transparent)}
.badge.edit{border-color:color-mix(in srgb,var(--edit) 55%,transparent);background:color-mix(in srgb,var(--edit) 14%,transparent)}
.timeline li.new{background:color-mix(in srgb,var(--new) 8%,transparent)}
h3.sub{margin:22px 0 8px;font-size:1.05rem;font-weight:700;color:var(--txt)}
.semdata{list-style:none;margin:0;padding:0}
.semdata li{padding:10px 0;border-bottom:1px solid var(--line);font-size:.93rem;overflow-wrap:anywhere}
.semdata li:last-child{border-bottom:0}
.semdata .inf{color:var(--mut)}
.legenda{margin:10px 0 0;font-size:.8rem;color:var(--mut)}
footer{text-align:center;color:var(--mut);font-size:.8rem;padding:26px 20px 40px}
@media (min-width:700px){
 body{font-size:16px}
 header.top{padding:44px 32px 28px}
 header.top h1{font-size:2.4rem}
 nav.chips{padding:12px 32px;justify-content:center;flex-wrap:wrap}
 main{padding:4px 28px 52px}
 section.sec{padding:24px 24px 22px}
 .grid{grid-template-columns:repeat(2,minmax(0,1fr))}
 .timeline li{grid-template-columns:100px 1fr}
 .timeline .inf{display:inline;margin-left:8px}
}
@media (min-width:1050px){.grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
"""


def build(data):
    try:
        dt = datetime.fromisoformat(data["atualizado_em"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
    except (KeyError, ValueError, TypeError):
        dt = datetime.now(TZ)
    secs = data["secoes"]
    chips, blocos = [], []
    for key, chip in ORDEM:
        sec = secs.get(key)
        if not sec:
            continue
        n = len(sec.get("itens", []))
        a = ANCORA[key]
        chips.append(f'<a href="#{a}" class="s-{a}">{e(sec["emoji"])} {e(chip)}<span class="n">{n}</span></a>')
        if key == "novidades":
            corpo = novidades_html(sec)
            corpo += '<p class="legenda">🆕 entrou hoje · ✏️ mudou hoje · 🧊 série na geladeira</p>'
        elif key == "filmes":
            corpo = f'<div class="grid">{"".join(card_filme(i) for i in sec["itens"])}</div>'
        elif key == "lancamentos":
            corpo = f'<div class="grid">{"".join(card_lancamento(i) for i in sec["itens"])}</div>'
        else:
            corpo = f'<div class="grid">{"".join(card_serie(i) for i in sec["itens"])}</div>'
        if n == 0:
            corpo = '<p class="legenda">Nada por aqui hoje.</p>'
        blocos.append(f'<section class="sec s-{a}" id="{a}"><h2>{e(sec["emoji"])} {e(sec["titulo"])}'
                      f'<span class="cnt">{n}</span></h2>{corpo}</section>')
    subtitulo = data.get("titulo", "")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#1c1f26" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f7f4ee" media="(prefers-color-scheme: light)">
<title>Séries do Murilo</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📺</text></svg>">
<style>{CSS}</style>
</head>
<body>
<header class="top">
<h1>Séries do <span>Murilo</span></h1>
<p class="sub1">{e(subtitulo)}</p>
<p class="upd">Atualizado em {e(fmt_data(dt))}</p>
</header>
<nav class="chips" aria-label="Seções">{"".join(chips)}</nav>
<main>
{"".join(blocos)}
</main>
<footer>Página gerada automaticamente a partir do resumo diário.</footer>
</body>
</html>
"""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "index.html"
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    html = build(data)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"ok: {dst} ({len(html)//1024} KB)")


if __name__ == "__main__":
    main()
