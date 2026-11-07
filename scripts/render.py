"""Renderiza um post (post.json) em JPEGs 1080x1350 prontos para o Instagram.

Uso: python scripts/render.py fila/2026-11-08/01
Gera slide-01.jpg, slide-02.jpg... dentro da pasta do post.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
FONTES = RAIZ / "assets" / "fonts"
W, H = 1080, 1350
MARGEM = 96

TEMAS = {
    "papel": {"fundo": "#F4EDE3", "texto": "#3B2A22", "suave": "#8C6E5D", "acento": "#B5643C", "linha": "#DCCBB8"},
    "cafe": {"fundo": "#2E211B", "texto": "#F4EDE3", "suave": "#C9B5A3", "acento": "#E0A27C", "linha": "#4A372D"},
    "rose": {"fundo": "#EAD6CC", "texto": "#3B2A22", "suave": "#7E5D50", "acento": "#9E4F35", "linha": "#D3B9AC"},
}


def fonte(nome, tam, peso=None):
    caminho = {
        "serif": "Lora-Variable.ttf",
        "serif_it": "Lora-Italic-Variable.ttf",
        "sans": "Inter-Medium.otf",
        "sans_b": "Inter-SemiBold.otf",
    }[nome]
    f = ImageFont.truetype(str(FONTES / caminho), tam)
    if peso and nome.startswith("serif"):
        if nome == "serif_it":
            peso = "Italic" if peso == "Regular" else f"{peso} Italic"
        f.set_variation_by_name(peso)
    return f


def aspas(texto):
    """Troca aspas retas por tipográficas."""
    out, abre = [], True
    for ch in texto:
        if ch == '"':
            out.append("\u201c" if abre else "\u201d")
            abre = not abre
        else:
            out.append(ch)
    return "".join(out)


def quebrar(draw, texto, f, largura):
    """Quebra o texto em linhas que cabem na largura, respeitando \n."""
    linhas = []
    for paragrafo in aspas(texto).split("\n"):
        palavras = paragrafo.split()
        if not palavras:
            linhas.append("")
            continue
        atual = palavras[0]
        for p in palavras[1:]:
            teste = atual + " " + p
            if draw.textlength(teste, font=f) <= largura:
                atual = teste
            else:
                linhas.append(atual)
                atual = p
        linhas.append(atual)
    return linhas


def bloco_ajustado(draw, texto, nome, peso, largura, altura_max, tam_max, tam_min, entre=1.32):
    """Escolhe o maior tamanho de fonte em que o bloco cabe na área."""
    for tam in range(tam_max, tam_min - 1, -2):
        f = fonte(nome, tam, peso)
        linhas = quebrar(draw, texto, f, largura)
        alt = int(len(linhas) * tam * entre)
        if alt <= altura_max:
            return f, linhas, tam, alt
    raise ValueError(f"Texto não cabe no slide mesmo em {tam_min}px: {texto[:60]}...")


def escrever(draw, x, y, linhas, f, tam, cor, entre=1.32, centro=False):
    for i, linha in enumerate(linhas):
        xx = x
        if centro:
            xx = (W - draw.textlength(linha, font=f)) / 2
        draw.text((xx, y + i * tam * entre), linha, font=f, fill=cor)


def xicara(draw, cx, cy, escala, cor):
    """Xícara de café em traço fino, motivo visual da marca."""
    s = escala
    lw = max(2, int(3 * s))
    draw.rounded_rectangle([cx - 34 * s, cy - 24 * s, cx + 26 * s, cy + 22 * s], radius=int(10 * s), outline=cor, width=lw)
    draw.arc([cx + 14 * s, cy - 14 * s, cx + 42 * s, cy + 10 * s], start=-90, end=90, fill=cor, width=lw)
    draw.line([cx - 48 * s, cy + 32 * s, cx + 40 * s, cy + 32 * s], fill=cor, width=lw)
    for dx in (-18, -2, 14):
        draw.arc([cx + (dx - 6) * s, cy - 58 * s, cx + (dx + 6) * s, cy - 32 * s], start=200, end=340, fill=cor, width=max(1, lw - 1))


def rodape(draw, t, marca, pagina=None, total=None, deslize=False):
    y = H - MARGEM + 10
    draw.line([MARGEM, y - 34, W - MARGEM, y - 34], fill=t["linha"], width=2)
    f = fonte("sans", 24)
    draw.text((MARGEM, y - 14), marca, font=f, fill=t["suave"])
    direita = ""
    if deslize:
        direita = "deslize  →"
    elif pagina and total:
        direita = f"{pagina}/{total}"
    if direita:
        draw.text((W - MARGEM - draw.textlength(direita, font=f), y - 14), direita, font=f, fill=t["suave"])


def etiqueta(draw, t, texto, y=MARGEM):
    f = fonte("sans_b", 24)
    txt = texto.upper()
    espaco = " ".join(txt)  # espaçamento de letras
    draw.text((MARGEM, y), espaco, font=f, fill=t["acento"])
    return y + 60


def slide_capa(draw, t, s, marca):
    etiqueta(draw, t, s.get("etiqueta", ""))
    area_alt = 760
    f, linhas, tam, alt = bloco_ajustado(draw, s["titulo"], "serif", "SemiBold", W - 2 * MARGEM, area_alt, 96, 52, 1.18)
    y = 300 + (area_alt - alt) // 2
    escrever(draw, MARGEM, y, linhas, f, tam, t["texto"], 1.18)
    if s.get("subtitulo"):
        fs, ls, ts, _ = bloco_ajustado(draw, s["subtitulo"], "serif_it", "Regular", W - 2 * MARGEM, 140, 40, 30)
        escrever(draw, MARGEM, y + alt + 36, ls, fs, ts, t["suave"])
    xicara(draw, W - MARGEM - 50, 150, 1.2, t["acento"])
    rodape(draw, t, marca, deslize=True)


def slide_texto(draw, t, s, marca, n, total):
    y = MARGEM + 20
    if s.get("titulo"):
        f, linhas, tam, alt = bloco_ajustado(draw, s["titulo"], "serif", "Bold", W - 2 * MARGEM, 260, 62, 44, 1.2)
        escrever(draw, MARGEM, y, linhas, f, tam, t["acento"], 1.2)
        y += alt + 48
    disp = H - MARGEM - 70 - y
    f, linhas, tam, alt = bloco_ajustado(draw, s["texto"], "serif", "Regular", W - 2 * MARGEM, disp, 64, 36, 1.4)
    escrever(draw, MARGEM, y + max(0, int((disp - alt) / 2.6)), linhas, f, tam, t["texto"], 1.4)
    rodape(draw, t, marca, n, total)


def slide_lista(draw, t, s, marca, n, total):
    y = MARGEM + 20
    if s.get("titulo"):
        f, linhas, tam, alt = bloco_ajustado(draw, s["titulo"], "serif", "Bold", W - 2 * MARGEM, 220, 58, 42, 1.2)
        escrever(draw, MARGEM, y, linhas, f, tam, t["acento"], 1.2)
        y += alt + 44
    itens = s["itens"]
    disp = H - MARGEM - 70 - y
    larg = W - 2 * MARGEM - 70
    for tam in range(44, 29, -2):
        f = fonte("serif", tam, "Regular")
        blocos = [quebrar(draw, it, f, larg) for it in itens]
        alt = sum(len(b) * tam * 1.36 for b in blocos) + (len(itens) - 1) * tam * 0.9
        if alt <= disp:
            break
    else:
        raise ValueError("Lista não cabe no slide")
    fn = fonte("serif", tam, "Bold")
    for i, b in enumerate(blocos, 1):
        draw.text((MARGEM, y), f"{i}.", font=fn, fill=t["acento"])
        escrever(draw, MARGEM + 70, y, b, f, tam, t["texto"], 1.36)
        y += len(b) * tam * 1.36 + tam * 0.9
    rodape(draw, t, marca, n, total)


def slide_frase(draw, t, s, marca, n=None, total=None):
    """Estático de frase ou trecho de carta: centralizado, itálico."""
    if s.get("etiqueta"):
        etiqueta(draw, t, s["etiqueta"])
    area = 820
    f, linhas, tam, alt = bloco_ajustado(draw, s["texto"], "serif_it", "Medium", W - 2 * MARGEM - 40, area, 78, 44, 1.3)
    y = (H - alt) // 2 - 30
    fa = fonte("serif", 160, "Bold")
    draw.text((MARGEM - 10, y - 150), "“", font=fa, fill=t["linha"])
    escrever(draw, 0, y, linhas, f, tam, t["texto"], 1.3, centro=True)
    if s.get("assinatura"):
        fs = fonte("sans", 28)
        a = s["assinatura"]
        draw.text(((W - draw.textlength(a, font=fs)) / 2, y + alt + 40), a, font=fs, fill=t["suave"])
    xicara(draw, W // 2, H - MARGEM - 120, 0.9, t["acento"])
    rodape(draw, t, marca, n, total)


def slide_fechamento(draw, t, s, marca, n, total):
    xicara(draw, W // 2, 330, 1.6, t["acento"])
    area = 420
    f, linhas, tam, alt = bloco_ajustado(draw, s["titulo"], "serif", "SemiBold", W - 2 * MARGEM, area, 70, 44, 1.22)
    y = 480
    escrever(draw, 0, y, linhas, f, tam, t["texto"], 1.22, centro=True)
    y += alt + 50
    if s.get("texto"):
        fs, ls, ts, al = bloco_ajustado(draw, s["texto"], "serif_it", "Regular", W - 2 * MARGEM - 60, 260, 40, 30, 1.36)
        escrever(draw, 0, y, ls, fs, ts, t["suave"], 1.36, centro=True)
    rodape(draw, t, marca, n, total)


def renderizar(pasta):
    pasta = Path(pasta)
    post = json.loads((pasta / "post.json").read_text(encoding="utf-8"))
    marca = json.loads((RAIZ / "marca.json").read_text(encoding="utf-8"))["assinatura_rodape"]
    t = TEMAS[post.get("tema", "papel")]
    slides = post["slides"]
    total = len(slides)
    for velho in pasta.glob("slide-*.jpg"):
        velho.unlink()
    saida = []
    for n, s in enumerate(slides, 1):
        img = Image.new("RGB", (W, H), t["fundo"])
        d = ImageDraw.Draw(img)
        lay = s["layout"]
        if lay == "capa":
            slide_capa(d, t, s, marca)
        elif lay == "texto":
            slide_texto(d, t, s, marca, n, total)
        elif lay == "lista":
            slide_lista(d, t, s, marca, n, total)
        elif lay == "frase":
            slide_frase(d, t, s, marca, n if total > 1 else None, total if total > 1 else None)
        elif lay == "fechamento":
            slide_fechamento(d, t, s, marca, n, total)
        else:
            raise ValueError(f"Layout desconhecido: {lay}")
        arq = pasta / f"slide-{n:02d}.jpg"
        img.save(arq, "JPEG", quality=90, optimize=True, progressive=False)
        saida.append(arq.name)
    return saida


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, renderizar(p))
