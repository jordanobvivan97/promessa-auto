"""Valida posts da fila antes de renderizar/publicar. Sai com código 1 se houver erro.

Uso: python scripts/validar.py fila/2026-11-08
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PROIBIDOS = ["—", "–"]  # travessões: regra da marca
JARGAO = ["gatilho mental", "high value", "energia masculina", "vibrar alto", "mulher de valor", "narcisista"]
SENSIVEIS = ["violência", "agress", "abuso", "bate", "ameaça", "suicíd", "medo constante"]
LAYOUTS = {"capa", "texto", "lista", "frase", "fechamento"}


def pautas_recentes(dias=30, excluir=None):
    limite = date.today() - timedelta(days=dias)
    usadas = {}
    for base in ("fila", "publicados"):
        for pj in (RAIZ / base).glob("*/*/post.json"):
            if excluir and pj.parent.resolve() == Path(excluir).resolve():
                continue
            try:
                d = date.fromisoformat(pj.parent.parent.name)
            except ValueError:
                continue
            if d >= limite:
                p = json.loads(pj.read_text(encoding="utf-8"))
                usadas.setdefault(p.get("pauta_id"), []).append(str(pj.parent.relative_to(RAIZ)))
    return usadas


def todos_textos(p):
    out = [p.get("legenda", "")]
    for s in p["slides"]:
        for k in ("titulo", "subtitulo", "texto", "etiqueta", "assinatura"):
            if s.get(k):
                out.append(s[k])
        out += s.get("itens", [])
    return out


def validar_post(pasta):
    erros, avisos = [], []
    p = json.loads((pasta / "post.json").read_text(encoding="utf-8"))
    for campo in ("id", "pauta_id", "tipo", "horario", "slides", "legenda", "ebook"):
        if campo not in p:
            erros.append(f"falta o campo '{campo}'")
    if erros:
        return erros, avisos
    n = len(p["slides"])
    if p["tipo"] == "estatico" and n != 1:
        erros.append("estático precisa de exatamente 1 slide")
    if p["tipo"] == "carrossel" and not (3 <= n <= 10):
        erros.append("carrossel precisa de 3 a 10 slides (limite da API: 10)")
    if not re.fullmatch(r"\d{2}:\d{2}", p["horario"]):
        erros.append("horario deve ser HH:MM")
    for s in p["slides"]:
        if s.get("layout") not in LAYOUTS:
            erros.append(f"layout inválido: {s.get('layout')}")
    textos = todos_textos(p)
    junto = "\n".join(textos)
    for ch in PROIBIDOS:
        if ch in junto:
            erros.append("contém travessão (proibido pela marca)")
    for j in JARGAO:
        if j in junto.lower():
            erros.append(f"jargão de coach/psicologia pop: '{j}'")
    if len(p["legenda"]) > 2200:
        erros.append("legenda acima de 2200 caracteres")
    tags = re.findall(r"#\w+", p["legenda"])
    if len(tags) > 5:
        erros.append("mais de 5 hashtags")
    if any(w in junto.lower() for w in SENSIVEIS) and not ("180" in p["legenda"] or "188" in p["legenda"]):
        erros.append("tema sensível sem indicação de ajuda (Ligue 180 / CVV 188) na legenda")
    if "link na bio" in junto.lower():
        marca = json.loads((RAIZ / "marca.json").read_text(encoding="utf-8"))
        if not marca.get("link_bio_ativo"):
            erros.append("CTA de link na bio, mas a página de vendas ainda não está ativa")
    usadas = pautas_recentes(excluir=pasta)
    if p["pauta_id"] in usadas:
        erros.append(f"pauta repetida nos últimos 30 dias: {usadas[p['pauta_id']]}")
    if p["tipo"] == "carrossel" and p["slides"][0]["layout"] != "capa":
        avisos.append("carrossel sem capa no primeiro slide")
    return erros, avisos


def main(alvos):
    falhou = False
    pastas = []
    for a in alvos:
        a = Path(a)
        pastas += [a] if (a / "post.json").exists() else sorted(x for x in a.iterdir() if (x / "post.json").exists())
    for pasta in pastas:
        erros, avisos = validar_post(pasta)
        estado = "ERRO" if erros else "ok"
        print(f"[{estado}] {pasta}")
        for e in erros:
            print("   x", e)
        for w in avisos:
            print("   !", w)
        falhou |= bool(erros)
    sys.exit(1 if falhou else 0)


if __name__ == "__main__":
    main(sys.argv[1:] or ["fila"])
