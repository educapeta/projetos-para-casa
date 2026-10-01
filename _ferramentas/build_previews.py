# -*- coding: utf-8 -*-
"""Gera as imagens de cada pasta de modelagem: preview.png e partes.png.

Uso:
    python build_previews.py [pasta-raiz]

- `pasta-raiz` (padrao: a pasta acima deste script) deve conter uma subpasta por modelagem.
- preview.png  -> imagem principal (a peca mais representativa da pasta)
- partes.png   -> folha de contato com todas as pecas + legenda (quando ha 2+ malhas)
- Requer apenas Pillow; o renderizador esta em render_stl.py (mesma pasta).
"""
import os
import sys
import tempfile
import traceback

from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import render_stl  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(AQUI)
LOG = os.path.join(tempfile.gettempdir(), "previews-3d.log")

TILE_W, TILE_H = 420, 330
COLS = 3


def fonte(tam, negrito=False):
    """Fonte do sistema, com caminhos alternativos (Windows/Linux)."""
    candidatos = [
        r"C:\Windows\Fonts\arialbd.ttf" if negrito else r"C:\Windows\Fonts\arial.ttf",
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if negrito
         else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for p in candidatos:
        if os.path.exists(p):
            return ImageFont.truetype(p, tam)
    return ImageFont.load_default()


def log(msg):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(msg + "\n")
    try:
        print(msg)
    except Exception:
        pass


def pick_main(malhas):
    """Escolhe a malha mais representativa: montagem > maior arquivo."""
    mont = [p for p in malhas if os.path.basename(p).lower().startswith("montagem")]
    pool = mont if mont else malhas
    return max(pool, key=os.path.getsize)


def nice(name):
    for ext in (".stl", ".STL", ".obj", ".OBJ"):
        if name.endswith(ext):
            name = name[: -len(ext)]
    return name.replace("_", " ").strip()


def contact_sheet(malhas, out_path):
    vistos = set()
    unicos = []
    for p in malhas:                      # sem repetidos de mesmo nome
        nome = os.path.basename(p).lower()
        if nome not in vistos:
            vistos.add(nome)
            unicos.append(p)
    malhas = unicos

    f_reg = fonte(17)
    f_negr = fonte(18, negrito=True)
    linhas = (len(malhas) + COLS - 1) // COLS
    W, H = TILE_W * COLS, TILE_H * linhas + 46
    folha = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(folha)
    dr.text((16, 14), "Partes do projeto", font=f_negr, fill=(60, 80, 110))
    for i, p in enumerate(malhas):
        cx = (i % COLS) * TILE_W
        cy = 46 + (i // COLS) * TILE_H
        try:
            img = render_stl.render(render_stl.read_mesh(p), TILE_W - 24, TILE_H - 54)
        except Exception:
            log("  [ERRO render tile] %s\n%s" % (p, traceback.format_exc()))
            continue
        folha.paste(img, (cx + 12, cy + 6))
        dr.rectangle([cx + 12, cy + 6, cx + TILE_W - 12, cy + TILE_H - 48],
                     outline=(222, 230, 240))
        rotulo = nice(os.path.basename(p))
        if len(rotulo) > 44:
            rotulo = rotulo[:41] + "..."
        dr.text((cx + 16, cy + TILE_H - 40), rotulo, font=f_reg, fill=(70, 70, 80))
    folha.save(out_path, "PNG", optimize=True)
    return folha.size


def main():
    open(LOG, "w", encoding="utf-8").close()
    log("=== PREVIEWS DE %s ===" % ROOT)
    pastas = sorted(
        d for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d)) and d != ".git"
    )
    for pasta in pastas:
        base = os.path.join(ROOT, pasta)
        malhas = []
        for raiz, _dirs, arquivos in os.walk(base):
            for f in arquivos:
                if f.lower().endswith((".stl", ".obj")):
                    malhas.append(os.path.join(raiz, f))
        malhas.sort(key=lambda p: (-os.path.getsize(p), p))
        if not malhas:
            log("[%s] sem malha -> sem preview" % pasta)
            continue

        principal = pick_main(malhas)
        try:
            img = render_stl.render(render_stl.read_mesh(principal), 900, 675)
            img.save(os.path.join(base, "preview.png"), "PNG", optimize=True)
            log("[%s] preview.png <- %s" % (pasta, os.path.basename(principal)))
        except Exception:
            log("[%s] FALHA no preview:\n%s" % (pasta, traceback.format_exc()))

        if len(malhas) > 1:
            try:
                w, h = contact_sheet(malhas[:9], os.path.join(base, "partes.png"))
                log("[%s] partes.png (%d pecas, %dx%d)"
                    % (pasta, min(len(malhas), 9), w, h))
            except Exception:
                log("[%s] FALHA na folha de contato:\n%s" % (pasta, traceback.format_exc()))
    log("=== FIM ===")


if __name__ == "__main__":
    main()
