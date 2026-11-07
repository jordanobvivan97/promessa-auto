"""Publica no Instagram os posts da fila cujo horário já chegou (roda no GitHub Actions).

Regras:
- Só publica o que está na branch principal (aprovação = PR mergeado).
- Fuso: America/Sao_Paulo. Posts de dias anteriores não publicados são ignorados
  (não despeja atraso de uma vez), exceto se tiverem "recuperar": true.
- Depois de publicar, move a pasta para publicados/ e grava publicado.json.

Variáveis de ambiente: IG_USER_ID, IG_TOKEN, GITHUB_REPOSITORY, GITHUB_SHA.
"""
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

RAIZ = Path(__file__).resolve().parent.parent
TZ = ZoneInfo("America/Sao_Paulo")
API = os.environ.get("IG_API_BASE", "https://graph.instagram.com/v24.0")
IG_USER = os.environ["IG_USER_ID"]
TOKEN = os.environ["IG_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]
SHA = os.environ["GITHUB_SHA"]
MAX_POR_EXECUCAO = 1  # evita rajada: no máximo 1 post a cada execução


def url_imagem(caminho_rel, provedor="jsdelivr"):
    if provedor == "jsdelivr":
        return f"https://cdn.jsdelivr.net/gh/{REPO}@{SHA}/{caminho_rel}"
    return f"https://raw.githubusercontent.com/{REPO}/{SHA}/{caminho_rel}"


def chamar(metodo, caminho, **params):
    params["access_token"] = TOKEN
    r = requests.request(metodo, f"{API}/{caminho}", data=params if metodo == "POST" else None,
                         params=params if metodo == "GET" else None, timeout=60)
    dados = r.json()
    if "error" in dados:
        raise RuntimeError(f"{caminho}: {dados['error']}")
    return dados


def esperar_container(cid, limite=180):
    inicio = time.time()
    while time.time() - inicio < limite:
        st = chamar("GET", cid, fields="status_code,status")
        if st.get("status_code") == "FINISHED":
            return
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {cid} falhou: {st}")
        time.sleep(5)
    raise TimeoutError(f"container {cid} não ficou pronto em {limite}s")


def criar_containers(pasta, post, provedor):
    rel = pasta.relative_to(RAIZ).as_posix()
    imagens = sorted(pasta.glob("slide-*.jpg"))
    if post["tipo"] == "estatico":
        c = chamar("POST", f"{IG_USER}/media", image_url=url_imagem(f"{rel}/{imagens[0].name}", provedor),
                   caption=post["legenda"])
        esperar_container(c["id"])
        return c["id"]
    filhos = []
    for img in imagens:
        c = chamar("POST", f"{IG_USER}/media", image_url=url_imagem(f"{rel}/{img.name}", provedor),
                   is_carousel_item="true")
        filhos.append(c["id"])
    for f in filhos:
        esperar_container(f)
    c = chamar("POST", f"{IG_USER}/media", media_type="CAROUSEL", children=",".join(filhos), caption=post["legenda"])
    esperar_container(c["id"])
    return c["id"]


def publicar(pasta):
    post = json.loads((pasta / "post.json").read_text(encoding="utf-8"))
    try:
        cid = criar_containers(pasta, post, "jsdelivr")
    except RuntimeError as e:
        print(f"jsDelivr falhou ({e}); tentando raw.githubusercontent", file=sys.stderr)
        cid = criar_containers(pasta, post, "raw")
    pub = chamar("POST", f"{IG_USER}/media_publish", creation_id=cid)
    info = chamar("GET", pub["id"], fields="id,permalink,timestamp")
    destino = RAIZ / "publicados" / pasta.parent.name / pasta.name
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(pasta), destino)
    (destino / "publicado.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Publicado {post['id']}: {info.get('permalink')}")


def pendentes(agora):
    hoje = agora.date().isoformat()
    lista = []
    for pj in sorted((RAIZ / "fila").glob("*/*/post.json")):
        pasta = pj.parent
        post = json.loads(pj.read_text(encoding="utf-8"))
        dia = pasta.parent.name
        if dia > hoje:
            continue
        if dia < hoje and not post.get("recuperar"):
            continue
        h, m = map(int, post["horario"].split(":"))
        if dia == hoje and (agora.hour, agora.minute) < (h, m):
            continue
        if not list(pasta.glob("slide-*.jpg")):
            print(f"Sem imagens renderizadas em {pasta}, pulando", file=sys.stderr)
            continue
        lista.append(pasta)
    return lista


def main():
    agora = datetime.now(TZ)
    if (RAIZ / "PAUSADO").exists():
        print("Arquivo PAUSADO presente: nada será publicado.")
        return
    fila = pendentes(agora)
    print(f"{agora:%Y-%m-%d %H:%M} BRT, {len(fila)} post(s) no horário")
    erros = 0
    for pasta in fila[:MAX_POR_EXECUCAO]:
        try:
            publicar(pasta)
        except Exception as e:  # noqa: BLE001
            erros += 1
            print(f"ERRO ao publicar {pasta}: {e}", file=sys.stderr)
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
