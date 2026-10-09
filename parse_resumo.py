#!/usr/bin/env python3
"""Converte o resumo diário de séries (markdown, formato canônico das 8h) em data.json.

Uso:
  python3 parse_resumo.py RESUMO-series.md [--filmes RESUMO-filmes.md] [--extra novidades.md ...] [-o data.json]

--filmes: resumo de filmes do dia (padrão: resumo-AAAA-MM-DD-filmes.md ao lado
do resumo de séries). Vira a seção "filmes" (última). Parsing estrito.
--extra: arquivos com linhas de novidade já no formato do resumo
("[🆕|🧊|✏️ ]DD/MM[/AAAA] (dow) - Nome - Tn - info"). Linhas que ainda não
estão no resumo são inseridas na lista de Novidades, em ordem de data.
O texto é copiado literalmente; nada é inventado.
"""
import argparse, json, os, re, sys
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
SEP = re.compile(r"^_{3,}\s*$")
BADGES = ("🆕", "🧊", "✏️", "🔜")
NOV_RE = re.compile(r"^(?:(🆕|🧊|✏️)\s+)?(\d{2}/\d{2}(?:/\d{4})?)\s+\(([^)]+)\)\s+-\s+(.+)$")

SECTIONS = {
    "🎬 Lançamentos de hoje": ("lancamentos", "🎬"),
    "🆕 Novidades de streaming no Brasil": ("novidades", "🆕"),
    "⏳ Ativas atrasadas": ("ativas_atrasadas", "⏳"),
    "📺 Episódio recente": ("episodio_recente", "📺"),
    "📅 Episódio de hoje": ("episodio_hoje", "📅"),
    "⏳ Finalizadas atrasadas": ("finalizadas_atrasadas", "⏳"),
}


def split_name(full):
    """'Nome PT (Original)' -> (nome, original|None)."""
    m = re.match(r"^(.*\S)\s+\(([^()]+)\)$", full)
    if m:
        return m.group(1), m.group(2)
    return full, None


def progress(txt):
    m = re.match(r"^(\d+)/(\d+)$", txt.strip())
    if not m:
        return {"texto": txt.strip(), "vistos": None, "total": None}
    return {"texto": txt.strip(), "vistos": int(m.group(1)), "total": int(m.group(2))}


def episode(txt):
    """'5x05 - EN / PT' -> dict. Mantém o texto bruto em 'texto'."""
    d = {"texto": txt, "codigo": txt, "titulo_en": None, "titulo_pt": None}
    if " - " in txt:
        code, rest = txt.split(" - ", 1)
        d["codigo"] = code
        if " / " in rest:
            en, pt = rest.split(" / ", 1)
            d["titulo_en"], d["titulo_pt"] = en, pt
        else:
            d["titulo_en"] = rest
    return d


def add_line(item, line):
    for key, pre in (("titulo_pt_nota", "📺 "), ("transmissao", "📡 "), ("brasil", "🇧🇷 ")):
        if line.startswith(pre):
            item[key] = line[len(pre):]
            return
    if line.startswith("ℹ️ "):
        item.setdefault("notas", []).append(line[len("ℹ️ "):])
        return
    item.setdefault("outras_linhas", []).append(line)


def parse_series_block(lines):
    head = lines[0]
    m = re.match(r"^\*\*(.+?)\*\*\s*(🟢|🔴)?\s*$", head)
    if not m:
        raise ValueError(f"cabeçalho de série inesperado: {head!r}")
    nome, orig = split_name(m.group(1))
    item = {"nome": nome, "nome_original": orig, "status": m.group(2) or ""}
    m2 = re.match(r"^(\S+)\s+·\s+(próximo|hoje):\s+(.+)$", lines[1])
    if not m2:
        raise ValueError(f"linha de progresso inesperada: {lines[1]!r}")
    item["progresso"] = progress(m2.group(1))
    ep = episode(m2.group(3))
    ep["rotulo"] = m2.group(2)
    item["proximo"] = ep
    for ln in lines[2:]:
        add_line(item, ln)
    return item


def parse_launch_block(lines):
    m = re.match(r"^\*\*(.+)\*\*$", lines[0])
    full = m.group(1)
    name_part, code, prog = full.rsplit(" - ", 2)
    nome, orig = split_name(name_part)
    item = {"nome": nome, "nome_original": orig, "episodios": code, "progresso": progress(prog)}
    for ln in lines[1:]:
        add_line(item, ln)
    return item


def parse_novidade(line):
    m = NOV_RE.match(line)
    if not m:
        return None
    badge, data, dow, rest = m.groups()
    parts = rest.split(" - ", 2)
    nome = parts[0]
    temporada = parts[1] if len(parts) > 1 else ""
    info = parts[2] if len(parts) > 2 else ""
    return {"selo": badge or "", "data": data, "dia_semana": dow, "nome": nome,
            "temporada": temporada, "info": info, "texto": line}


def nov_sort_key(n, default_year):
    d = n["data"].split("/")
    y = int(d[2]) if len(d) == 3 else default_year
    return (y, int(d[1]), int(d[0]))


def blocks(lines):
    cur = []
    for ln in lines:
        if SEP.match(ln):
            if cur:
                yield cur
            cur = []
        elif ln.strip():
            cur.append(ln.rstrip())
    if cur:
        yield cur


def parse(md_text):
    lines = md_text.splitlines()
    data = {"titulo": "", "secoes": {}}
    # título
    m = re.match(r"^\*\*(📺 Séries — .+)\*\*$", lines[0].strip())
    data["titulo"] = m.group(1) if m else lines[0].strip("* ")
    # fatiar por seção
    current, buf, chunks = None, [], {}
    for ln in lines[1:]:
        s = ln.strip()
        title = s.strip("*")
        if s.startswith("**") and title in SECTIONS:
            if current:
                chunks[current] = buf
            current, buf = title, []
        elif current:
            buf.append(ln)
    if current:
        chunks[current] = buf

    for title, body in chunks.items():
        key, emoji = SECTIONS[title]
        sec = {"titulo": title.split(" ", 1)[1], "emoji": emoji}
        if key == "lancamentos":
            sec["itens"] = [parse_launch_block(b) for b in blocks(body)]
        elif key == "novidades":
            nov, sem = [], []
            mode = "nov"
            for ln in body:
                s = ln.strip()
                if not s or SEP.match(s):
                    continue
                if s.strip("*") == "Ainda sem data no Brasil":
                    mode = "sem"
                    continue
                if mode == "nov":
                    n = parse_novidade(s)
                    if not n:
                        raise ValueError(f"novidade fora do formato: {s!r}")
                    nov.append(n)
                else:
                    nome, _, resto = s.partition(" - ")
                    sem.append({"nome": nome, "info": resto, "texto": s})
            sec["itens"] = nov
            sec["sem_data"] = {"titulo": "Ainda sem data no Brasil", "itens": sem}
        else:
            sec["itens"] = [parse_series_block(b) for b in blocks(body)]
        data["secoes"][key] = sec
    return data


# ---------------------------------------------------------------- filmes
FILM_FIELDS = [
    ("🏷️", "Tipo de lançamento", "tipo_lancamento"),
    ("🎟️", "Cinema no Brasil", "cinema_brasil"),
    ("🛒", "Aluguel e compra", "aluguel_compra"),
    ("📺", "Streaming", "streaming"),
]
FILM_TITLE_RE = re.compile(r"^\*\*(.+?) \((.+), (\d{4})\)\*\*$")
FIELD_RE = re.compile(r"^(🏷️|🎟️|🛒|📺) \*\*([^*]+):\*\*(?: (.+))?$")


def parse_film_block(lines):
    m = FILM_TITLE_RE.match(lines[0])
    if not m:
        raise ValueError(f"título de filme fora do formato: {lines[0]!r}")
    film = {"titulo": m.group(1), "titulo_original": m.group(2), "ano": m.group(3)}
    valid = {(e, r): k for e, r, k in FILM_FIELDS}
    cur = None
    for ln in lines[1:]:
        fm = FIELD_RE.match(ln)
        if fm:
            key = valid.get((fm.group(1), fm.group(2)))
            if not key:
                raise ValueError(f"campo de filme desconhecido: {ln!r}")
            if key in film:
                raise ValueError(f"campo repetido em {film['titulo']}: {ln!r}")
            cur = {"emoji": fm.group(1), "rotulo": fm.group(2), "valor": fm.group(3), "notas": []}
            if key in ("aluguel_compra", "streaming"):
                cur["linhas"] = []
            film[key] = cur
        elif ln.startswith("ℹ️ "):
            if cur is None:
                raise ValueError(f"nota ℹ️ antes de qualquer campo: {ln!r}")
            cur["notas"].append(ln[len("ℹ️ "):])
        else:
            if cur is None or "linhas" not in cur or cur["valor"] is not None or cur["notas"]:
                raise ValueError(f"linha de filme inesperada em {film['titulo']}: {ln!r}")
            loja, sep, txt = ln.partition(": ")
            cur["linhas"].append({"loja": loja, "texto": txt} if sep else {"loja": None, "texto": ln})
    faltam = [r for _, r, k in FILM_FIELDS if k not in film]
    if faltam:
        raise ValueError(f"{film['titulo']}: faltam campos {faltam}")
    return film


def parse_filmes(md_text):
    lines = [l.rstrip() for l in md_text.splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines[0].strip() != "**🎞️ Filmes**":
        raise ValueError(f"resumo de filmes deve começar com **🎞️ Filmes**: {lines[0]!r}")
    return {"titulo": "Filmes", "emoji": "🎞️", "itens": [parse_film_block(b) for b in blocks(lines[1:])]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("resumo")
    ap.add_argument("--extra", action="append", default=[])
    ap.add_argument("--filmes", help="resumo-AAAA-MM-DD-filmes.md (padrão: o arquivo -filmes.md irmão do resumo, se existir)")
    ap.add_argument("--sem-filmes", action="store_true", help="não incluir a seção Filmes")
    ap.add_argument("-o", "--output", default="data.json")
    a = ap.parse_args()
    data = parse(open(a.resumo, encoding="utf-8").read())
    year = int(re.search(r"(\d{4})", data["titulo"]).group(1)) if re.search(r"\d{4}", data["titulo"]) else datetime.now(TZ).year
    nov = data["secoes"]["novidades"]["itens"]
    known = {(n["nome"], n["temporada"]) for n in nov}
    for path in a.extra:
        for ln in open(path, encoding="utf-8"):
            n = parse_novidade(ln.strip())
            if n and (n["nome"], n["temporada"]) not in known:
                nov.append(n)
                known.add((n["nome"], n["temporada"]))
                print(f"+ novidade extra: {n['texto']}", file=sys.stderr)
    nov.sort(key=lambda n: nov_sort_key(n, year))
    if not a.sem_filmes:
        fpath = a.filmes
        if not fpath and a.resumo.endswith("-series.md"):
            cand = a.resumo[: -len("-series.md")] + "-filmes.md"
            if os.path.exists(cand):
                fpath = cand
        if fpath:
            data["secoes"]["filmes"] = parse_filmes(open(fpath, encoding="utf-8").read())
            print(f"+ filmes: {fpath} ({len(data['secoes']['filmes']['itens'])})", file=sys.stderr)
        else:
            print("! sem resumo de filmes (use --filmes)", file=sys.stderr)
    data["atualizado_em"] = datetime.now(TZ).isoformat(timespec="minutes")
    out = {"titulo": data["titulo"], "atualizado_em": data["atualizado_em"], "secoes": data["secoes"]}
    with open(a.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"ok: {a.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
