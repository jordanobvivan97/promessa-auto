"""Coleta métricas dos posts publicados e calcula o freio de volume (roda no GitHub Actions).

Grava:
- metricas/posts.csv: uma linha por post (alcance, salvamentos, envios, curtidas, comentários)
- metricas/freio.json: volume recomendado de posts por dia para o gerador seguir

Lógica do freio: compara a mediana de alcance por post dos últimos N dias com os N dias
anteriores. Queda maior que o limite em marca.json reduz 1 post/dia (até o mínimo).
Estabilidade ou alta por duas janelas seguidas permite subir 1 (até o máximo).
Amostras com menos de 10 posts por janela não mexem no volume.
"""
import csv
import json
import os
import statistics
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
API = os.environ.get("IG_API_BASE", "https://graph.instagram.com/v24.0")
TOKEN = os.environ["IG_TOKEN"]
METRICAS = ["reach", "saved", "shares", "likes", "comments"]


def insights(media_id):
    r = requests.get(f"{API}/{media_id}/insights",
                     params={"metric": ",".join(METRICAS), "access_token": TOKEN}, timeout=60).json()
    if "error" in r:
        return {"erro": r["error"].get("message", "")}
    return {i["name"]: i["values"][0]["value"] for i in r.get("data", [])}


def coletar():
    linhas = []
    for pj in sorted((RAIZ / "publicados").glob("*/*/publicado.json")):
        pub = json.loads(pj.read_text(encoding="utf-8"))
        post = json.loads((pj.parent / "post.json").read_text(encoding="utf-8"))
        dados = insights(pub["id"])
        linhas.append({"data": pj.parent.parent.name, "id": post["id"], "pauta_id": post["pauta_id"],
                       "ebook": post["ebook"], "tipo": post["tipo"], "tema": post.get("tema", ""),
                       "horario": post["horario"], "permalink": pub.get("permalink", ""),
                       **{m: dados.get(m, "") for m in METRICAS}})
    (RAIZ / "metricas").mkdir(exist_ok=True)
    with open(RAIZ / "metricas" / "posts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()) if linhas else ["data"])
        w.writeheader()
        w.writerows(linhas)
    return linhas


def mediana_alcance(linhas, ini, fim):
    vals = [int(l["reach"]) for l in linhas if l["reach"] != "" and ini <= date.fromisoformat(l["data"]) < fim]
    return (statistics.median(vals) if vals else None), len(vals)


def freio(linhas):
    marca = json.loads((RAIZ / "marca.json").read_text(encoding="utf-8"))
    cfg = marca["freio"]
    arq = RAIZ / "metricas" / "freio.json"
    anterior = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    atual = anterior.get("posts_por_dia", marca["posts_por_dia"])
    n = cfg["janela_dias"]
    hoje = date.today() - timedelta(days=2)  # dá 2 dias para o alcance amadurecer
    rec, n_rec = mediana_alcance(linhas, hoje - timedelta(days=n), hoje)
    ant, n_ant = mediana_alcance(linhas, hoje - timedelta(days=2 * n), hoje - timedelta(days=n))
    decisao, motivo, estaveis = atual, "amostra insuficiente (menos de 10 posts por janela)", anterior.get("janelas_estaveis", 0)
    ultima = anterior.get("ultima_avaliacao")
    cedo = ultima and (date.today() - date.fromisoformat(ultima)).days < n
    if cedo:
        motivo = f"próxima avaliação após {n} dias da última ({ultima})"
    elif rec is not None and ant and n_rec >= 10 and n_ant >= 10:
        variacao = (rec - ant) / ant
        if variacao <= -cfg["queda_max_alcance_mediano"]:
            decisao = max(cfg["volume_minimo"], atual - 1)
            motivo, estaveis = f"alcance mediano caiu {variacao:.0%}: reduzir volume", 0
        else:
            estaveis += 1
            motivo = f"alcance mediano variou {variacao:+.0%}"
            if estaveis >= 2 and atual < cfg["volume_maximo"]:
                decisao, estaveis = atual + 1, 0
                motivo += ": duas janelas estáveis, subir 1 post/dia"
    saida = {"atualizado_em": datetime.now().isoformat(timespec="minutes"), "posts_por_dia": decisao,
             "mediana_recente": rec, "posts_recentes": n_rec, "mediana_anterior": ant, "posts_anteriores": n_ant,
             "janelas_estaveis": estaveis, "motivo": motivo,
             "ultima_avaliacao": ultima if cedo or rec is None or n_rec < 10 or n_ant < 10 else date.today().isoformat()}
    arq.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(saida, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    freio(coletar())
