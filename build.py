#!/usr/bin/env python3
"""Lê data.json e gera index.html (página única, CSS inline, sem JS).

Uso: python3 build.py [data.json] [index.html]
"""
import json, os, re, sys
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
    return f"{DIAS[dt.weekday()]}, {dt.day} de {MESES[dt.month-1]} de {dt.year}, às {dt:%Hh%M} (Horário de Brasília)"


def barra(p):
    if not p or p.get("total") in (None, 0):
        return ""
    pct = max(0, min(100, round(100 * p["vistos"] / p["total"])))
    return (f'<div class="prog"><div class="bar" role="progressbar" aria-valuenow="{p["vistos"]}" '
            f'aria-valuemin="0" aria-valuemax="{p["total"]}"><span style="width:{pct}%"></span></div>'
            f'<span class="ptxt">{e(p["texto"])}</span></div>')


def nome_html(it):
    s = f'<h3 class="nm">{e(it["nome"])}{selo_novo(it)}'
    if it.get("status"):
        s += f' <span class="dot">{e(it["status"])}</span>'
    s += "</h3>"
    if it.get("nome_original"):
        s += f'<p class="orig">{e(it["nome_original"])}</p>'
    return s


def linhas_extra(it):
    out = ""
    if it.get("titulo_pt_nota"):
        out += f'<p class="ln"><span class="ic">📺</span><span>{e(it["titulo_pt_nota"])}{sn(it, "titulo_pt_nota")}</span></p>'
    if it.get("transmissao"):
        out += f'<p class="ln"><span class="ic">📡</span><span>{e(it["transmissao"])}{sn(it, "transmissao")}</span></p>'
    if it.get("brasil"):
        out += f'<p class="ln br"><span class="ic">🇧🇷</span><span>{e(it["brasil"])}{sn(it, "brasil")}</span></p>'
    for n in it.get("notas", []):
        out += f'<p class="nota"><span class="ic">ℹ️</span><span>{e(n)}{sn(it, "notas:" + n)}</span></p>'
    for n in it.get("outras_linhas", []):
        out += f'<p class="nota"><span>{e(n)}</span></p>'
    return out


def duracao_html(d):
    if not d:
        return ""
    return f'<p class="ln dur"><span class="ic">⏱️</span><span>Duração: {e(d)}</span></p>'


def lancamento_html(iso):
    """⏳ contagem até o lançamento. Texto fixo é fallback; o JS recalcula no navegador."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return ""
    tem_hora = "T" in iso
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    dt = dt.astimezone(TZ)
    fb = f"{DIAS[dt.weekday()]}, {dt:%d/%m}" + (f", às {dt:%Hh%M}" if tem_hora else "")
    return (f'<p class="ln lanc" data-lanc="{e(iso)}" data-hora="{1 if tem_hora else 0}">'
            f'<span class="ic">⏳</span><span class="lt">Sai em: {e(fb)}</span></p>')


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
            f'<p class="ep"><span class="lbl">{e(ep["rotulo"])}</span> {ep_html}{sn(it, "proximo") or sn(it, "progresso")}</p>'
            f'{duracao_html(ep.get("duracao"))}{lancamento_html(ep.get("lancamento"))}{linhas_extra(it)}</article>')


def card_lancamento(it):
    return (f'<article class="card">{nome_html(it)}'
            f'<p class="ep"><span class="lbl">episódios</span> <b class="code">{e(it["episodios"])}</b>{sn(it, "episodios") or sn(it, "progresso")}</p>'
            f'{duracao_html(it.get("duracao"))}'
            f'{barra(it.get("progresso"))}{linhas_extra(it)}</article>')


DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]


def data_extenso(iso):
    """'2026-11-13' -> 'sexta-feira, 13 de novembro de 2026'"""
    d = datetime.fromisoformat(iso[:10])
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month-1]} de {d.year}"


def encomenda_html(enc, selo=""):
    """Linha 🛍️ de pré-venda/compra/aluguel digital no Brasil (encomendas-filmes.json)."""
    if not enc:
        return ""
    h = '<div class="enc">'
    if enc.get("ofertas"):
        for o in enc["ofertas"]:
            loja = e(o["loja"])
            if o.get("url"):
                loja = f'<a href="{e(o["url"])}" target="_blank" rel="noopener">{loja}</a>'
            dt = (f' · lança em {e(data_extenso(o["data_brasil"]))}' if o.get("data_brasil")
                  else " · data ainda não divulgada")
            preco = f' · {e(o["preco"])}' if o.get("preco") else ""
            h += f'<p class="encl"><span class="ic">🛍️</span><span><b class="enct">{e(o["tipo"])}</b> {loja}{preco}{dt}{selo}</span></p>'
            if o.get("fonte"):
                h += f'<p class="encv">{e(o["fonte"])}</p>'
    else:
        fonte = ""
        if enc.get("fonte_url"):
            fonte = f' (<a href="{e(enc["fonte_url"])}" target="_blank" rel="noopener">{e(enc.get("fonte_nome") or "fonte")}</a>)'
        h += (f'<p class="encl"><span class="ic">🛍️</span><span><b class="enct">digital</b> '
              f'ainda sem pré-venda, compra ou aluguel no Brasil{fonte}{selo}</span></p>')
    if enc.get("verificado_em"):
        h += f'<p class="encv">conferido em {e(data_extenso(enc["verificado_em"]))}</p>'
    return h + "</div>"


def aplicar_encomendas(data, path):
    """Copia encomendas-filmes.json para o campo `encomenda` de cada filme (titulo_original + ano)."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        itens = json.load(f).get("itens", [])
    idx = {(i["titulo_original"], str(i["ano"])): i for i in itens}
    for fl in data.get("secoes", {}).get("filmes", {}).get("itens", []):
        enc = idx.get((fl.get("titulo_original"), str(fl.get("ano"))))
        if enc:
            fl["encomenda"] = {k: v for k, v in enc.items() if k not in ("titulo_original", "ano")}
        else:
            fl.pop("encomenda", None)


# ---- selo "New" (regra do Murilo, 23/10/2026) ----
NOVO_HORAS = 24
VOLATEIS = {"verificado_em", "novo", "novo_ate", "progresso_barra", "campos_novos"}


def _limpo(x):
    if isinstance(x, dict):
        return {k: _limpo(v) for k, v in x.items() if k not in VOLATEIS}
    if isinstance(x, list):
        return [_limpo(v) for v in x]
    return x


def chave_item(sec, it):
    if sec == "filmes":
        return f'filmes|{it.get("titulo_original")}|{it.get("ano")}'
    if sec == "novidades":
        return f'novidades|{it.get("nome")}|{it.get("temporada")}'
    return f'{sec}|{it.get("nome")}'


def hash_item(it):
    import hashlib
    return hashlib.sha1(json.dumps(_limpo(it), ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def campos_item(it):
    """Campo -> hash. Notas e linhas de loja contam uma a uma (só a linha nova ganha o selo)."""
    out = {}
    for k, v in it.items():
        if k in VOLATEIS or k in ("campos_novos", "notas"):
            continue
        out[k] = hash_item(v)
    for n in it.get("notas", []) or []:
        out["notas:" + n] = "1"
    return out


def marcar_novos(data, path, agora=None):
    """Compara cada item com novos-itens.json. Item que apareceu ou mudou ganha `desde`=agora;
    fica `novo` por NOVO_HORAS horas. Grava o estado de volta."""
    from datetime import timedelta
    agora = agora or datetime.now(TZ)
    estado = {}
    if os.path.exists(path):
        estado = json.load(open(path, encoding="utf-8")).get("itens", {})
    vistos = set()
    pares = []
    for sec, conteudo in data.get("secoes", {}).items():
        pares += [(sec, it) for it in conteudo.get("itens", [])]
        if sec == "novidades":
            # Ainda sem data no Brasil (30/10/2026): item novo ou alterado também ganha o selo Novo
            pares += [("novidades_sem_data", it) for it in (conteudo.get("sem_data") or {}).get("itens", [])]
    for sec, it in pares:
            k, h = chave_item(sec, it), hash_item(it)
            vistos.add(k)
            st = estado.get(k)
            if not st or st.get("hash") != h:
                # mantém os hashes por campo: só a linha que mudou ganha o selo (corrigido 30/10/2026)
                st = estado[k] = {"hash": h, "desde": agora.isoformat(timespec="minutes"),
                                  "campos": (st or {}).get("campos", {})}
            # por campo (selo na linha que mudou)
            camp = st.setdefault("campos", {})
            novos_c = []
            for ck, chash in campos_item(it).items():
                c = camp.get(ck)
                if not c or c.get("hash") != chash:
                    c = camp[ck] = {"hash": chash, "desde": agora.isoformat(timespec="minutes")}
                if agora < datetime.fromisoformat(c["desde"]) + timedelta(hours=NOVO_HORAS):
                    novos_c.append(ck)
            atuais = set(campos_item(it))
            for ck in list(camp):
                if ck not in atuais:
                    del camp[ck]
            if novos_c:
                it["campos_novos"] = novos_c
            else:
                it.pop("campos_novos", None)
            ate = datetime.fromisoformat(st["desde"]) + timedelta(hours=NOVO_HORAS)
            if agora < ate:
                it["novo"] = True
                it["novo_ate"] = ate.isoformat(timespec="minutes")
            else:
                it.pop("novo", None); it.pop("novo_ate", None)
    # itens que saíram do site: esquece depois de 7 dias (se voltarem, contam como novos)
    for k in list(estado):
        if k not in vistos and agora - datetime.fromisoformat(estado[k]["desde"]) > timedelta(days=7):
            del estado[k]
    json.dump({"_leia": "Estado do selo New (build.py, marcar_novos). Chave = seção|item; hash do conteúdo; desde = quando apareceu/mudou. Novo por 24 h.",
               "itens": estado}, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def sn(it, campo):
    """Selo Novo na linha/campo que mudou."""
    if campo in (it.get("campos_novos") or []) and it.get("novo_ate"):
        return f' <span class="new" data-ate="{e(it["novo_ate"])}">Novo</span>'
    return ""


def selo_novo(it):
    if not it.get("novo"):
        return ""
    return f' <span class="new" data-ate="{e(it.get("novo_ate", ""))}">Novo</span>'


def card_filme(f):
    h = (f'<article class="card filme"><h3 class="nm">{e(f["titulo"])}{selo_novo(f)}</h3>'
         f'<p class="orig">{e(f["titulo_original"])} · {e(f["ano"])}</p>'
         f'{encomenda_html(f.get("encomenda"), sn(f, "encomenda"))}')
    for key in ("tipo_lancamento", "cinema_brasil", "aluguel_compra", "streaming"):
        c = f.get(key)
        if not c:
            continue
        h += f'<div class="fld"><p class="flbl"><span class="ic">{e(c["emoji"])}</span>{e(c["rotulo"])}{sn(f, key)}</p>'
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
                  f'<div class="tl"><b>{e(n["nome"])}</b> <span class="tmp">{e(n["temporada"])}</span>{selo_novo(n)}{badge}'
                  f'<span class="inf">{e(n["info"])}</span></div></li>')
    out = f'<ol class="timeline">{"".join(li)}</ol>'
    sd = sec.get("sem_data")
    if sd and sd.get("itens"):
        rows = ""
        for x in sd["itens"]:
            info = e(x["info"])
            if x.get("novo"):
                m = re.match(r"^(T\d+)\b", x["info"])
                info = (e(m.group(1)) + selo_novo(x) + e(x["info"][m.end():])) if m else info + selo_novo(x)
            rows += f'<li><b>{e(x["nome"])}</b> <span class="inf">{info}</span></li>'

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
span.new:not(.badge){display:inline-block;margin-left:6px;padding:1px 7px;border-radius:999px;background:var(--c,#d6ab8f);color:var(--bg);font-size:.62rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;line-height:1.5;vertical-align:2px;white-space:nowrap}
nav.chips a .new{margin-left:6px;vertical-align:1px}
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
.filme .enc{margin:8px 0 0}
.filme .encl{display:flex;gap:8px;margin:5px 0 0;font-size:.86rem;color:var(--txt2);overflow-wrap:anywhere}
.filme .enct{display:inline-block;font-size:.66rem;text-transform:uppercase;letter-spacing:.07em;font-weight:700;color:var(--c);border:1px solid var(--c);border-radius:999px;padding:1px 7px;margin-right:4px;vertical-align:1px}
.filme .encl a{color:var(--c)}
.filme .encv{margin:2px 0 0;padding-left:calc(1.3em + 8px);font-size:.76rem;color:var(--mut)}
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
        tem_novo = any(i.get("novo") for i in sec.get("itens", []) + (sec.get("sem_data") or {}).get("itens", []))
        nv = ' <span class="new">Novo</span>' if tem_novo else ""
        chips.append(f'<a href="#{a}" class="s-{a}">{e(sec["emoji"])} {e(chip)}<span class="n">{n}</span>{nv}</a>')
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
    subtitulo = re.sub(r"^(\S+\s+)?Séries(?=\s*—)", lambda m: (m.group(1) or "") + "Animes, Filmes e Séries", subtitulo, count=1)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta name="build-ts" content="{e(data.get('atualizado_em',''))}">
<meta name="color-scheme" content="dark light">
<meta name="theme-color" content="#1c1f26" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f7f4ee" media="(prefers-color-scheme: light)">
<title>Lista de Animes, Filmes e Séries do Murilo</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>📺</text></svg>">
<style>{CSS}</style>
</head>
<body>
<header class="top">
<h1>Lista de Animes, Filmes e Séries do <span>Murilo</span></h1>
<p class="sub1">{e(subtitulo)}</p>
<p class="upd">Atualizado em {e(fmt_data(dt))}</p>
</header>
<nav class="chips" aria-label="Seções">{"".join(chips)}</nav>
<main>
{"".join(blocos)}
</main>
<footer>Página gerada automaticamente a partir do resumo diário.</footer>
<script>
(function(){{
  /* selo New: some sozinho quando passam as 24 h (data-ate); a aba perde o New se a seção não tiver mais nenhum */
  var now=new Date();
  document.querySelectorAll('main .new[data-ate]').forEach(function(b){{var t=new Date(b.getAttribute('data-ate'));if(!isNaN(t)&&now>=t)b.remove();}});
  document.querySelectorAll('nav.chips a').forEach(function(a){{var s=document.querySelector(a.getAttribute('href'));var nb=a.querySelector('.new');if(nb&&s&&!s.querySelector('.new'))nb.remove();}});
}})();
(function(){{
  var D=['domingo','segunda-feira','terça-feira','quarta-feira','quinta-feira','sexta-feira','sábado'];
  function br(d){{var p={{}};new Intl.DateTimeFormat('en-CA',{{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23',weekday:'short'}}).formatToParts(d).forEach(function(x){{p[x.type]=x.value;}});return p;}}
  document.querySelectorAll('[data-lanc]').forEach(function(el){{
    var iso=el.getAttribute('data-lanc'),hora=el.getAttribute('data-hora')==='1';
    var s=iso.length===10?iso+'T00:00:00-03:00':(/[zZ]|[+-]\\d\\d:\\d\\d$/.test(iso)?iso:iso+'-03:00');
    var t=new Date(s);if(isNaN(t))return;
    var a=br(t),n=br(new Date());
    var dia=Date.UTC(+a.year,a.month-1,+a.day),hoje=Date.UTC(+n.year,n.month-1,+n.day);
    var dd=Math.round((dia-hoje)/864e5);
    if(dd<0||(hora&&t<new Date())){{el.remove();return;}}
    var wd=D[new Date(dia).getUTCDay()],h=hora?', às '+a.hour+'h'+a.minute:'';
    var txt=dd===0?'Sai hoje'+h:(dd===1?'Sai amanhã ('+wd+', '+a.day+'/'+a.month+h+')':'Sai em: '+dd+' dias ('+wd+', '+a.day+'/'+a.month+h+')');
    el.querySelector('.lt').textContent=txt;
  }});
}})();
(function(){{
  var cur=document.querySelector('meta[name="build-ts"]').content;
  function check(){{
    fetch(location.pathname+'?t='+Date.now(),{{cache:'no-store'}}).then(function(r){{return r.text();}}).then(function(t){{
      var m=t.match(/name="build-ts" content="([^"]+)"/);
      if(m&&m[1]!==cur){{location.replace(location.pathname+'?v='+encodeURIComponent(m[1])+location.hash);}}
    }}).catch(function(){{}});
  }}
  check();
  document.addEventListener('visibilitychange',function(){{if(!document.hidden)check();}});
  window.addEventListener('pageshow',function(ev){{if(ev.persisted)check();}});
}})();
</script>
</body>
</html>
"""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "data.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "index.html"
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    # filmes sempre em ordem de estreia no cinema no Brasil (regra do Murilo, 21/10/2026)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from parse_resumo import ordenar_filmes, remove_series_em_dia
    ordenar_filmes(data)
    # episódio/série já visto sai de lançamentos, Novidades e demais cards, mesmo no dia (regra 23/10/2026)
    remove_series_em_dia(data, os.path.join(os.path.dirname(os.path.abspath(__file__)), "series-em-dia.json"))
    # pré-venda/compra/aluguel digital no Brasil (encomendas-filmes.json, 23/10/2026)
    aplicar_encomendas(data, os.path.join(os.path.dirname(os.path.abspath(src)), "encomendas-filmes.json"))
    # selo New: compara com novos-itens.json (regra do Murilo, 23/10/2026)
    marcar_novos(data, os.path.join(os.path.dirname(os.path.abspath(src)), "novos-itens.json"))
    # sempre carimba a hora da atualização atual (regra do Murilo, 14/10/2026)
    data["atualizado_em"] = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M%z")[:-2] + ":" + datetime.now(TZ).strftime("%z")[-2:]
    with open(src, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    html = build(data)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"ok: {dst} ({len(html)//1024} KB)")


if __name__ == "__main__":
    main()
