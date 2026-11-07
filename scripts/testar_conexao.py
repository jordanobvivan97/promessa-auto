"""Teste só de leitura: confere se o token enxerga a conta do Instagram e a Página. Não publica nada.

Grava o resultado (sem o token) em metricas/teste-conexao.json.
"""
import json
import os
from datetime import datetime
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
API = os.environ.get("IG_API_BASE", "https://graph.facebook.com/v24.0")
TOKEN = os.environ["IG_TOKEN"]
IG = os.environ.get("IG_USER_ID", "").strip()
PAGE = os.environ.get("FB_PAGE_ID", "").strip()


def get(caminho, **params):
    params["access_token"] = TOKEN
    try:
        r = requests.get(f"{API}/{caminho}", params=params, timeout=60).json()
    except Exception as e:  # noqa: BLE001
        return {"erro": str(e)}
    if "error" in r:
        e = r["error"]
        return {"erro": e.get("message"), "codigo": e.get("code"), "subcodigo": e.get("error_subcode")}
    return r


res = {"em": datetime.now().isoformat(timespec="seconds")}
res["token"] = get("me", fields="id,name")
res["permissoes"] = get("me/permissions")
res["instagram"] = get(IG, fields="id,username,media_count") if IG else {"erro": "IG_USER_ID vazio"}
res["limite_publicacao"] = get(f"{IG}/content_publishing_limit", fields="config,quota_usage") if IG else None
res["pagina"] = get(PAGE, fields="id,name,instagram_business_account") if PAGE else {"erro": "FB_PAGE_ID vazio"}
if PAGE and "erro" not in res["pagina"]:
    tk = get(PAGE, fields="access_token")
    res["pagina_token_ok"] = "access_token" in tk
    if not res["pagina_token_ok"]:
        res["pagina_token_erro"] = tk
res["paginas_visiveis"] = get("me/accounts", fields="id,name")

(RAIZ / "metricas").mkdir(exist_ok=True)
(RAIZ / "metricas" / "teste-conexao.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(res, ensure_ascii=False, indent=2))
