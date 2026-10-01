"""Renderiza uma malha (.STL binario/ASCII ou .OBJ) em PNG usando apenas Pillow.

Uso:  python render_stl.py <arquivo.stl|.obj> <saida.png> [largura] [altura]

- Projecao isometrica 3/4 (sem perspectiva), algoritmo do pintor (z-sort).
- Sombreamento flat (por face) com luz direcional + ambiente + brilho suave.
- Antialiasing por supersampling 2x quando a malha nao e gigante.
"""
import math
import os
import struct
import sys

from PIL import Image, ImageDraw

# ------------------------------------------------------------------ leitura


def read_stl(path):
    """Retorna lista de tuplas (x1,y1,z1, x2,y2,z2, x3,y3,z3)."""
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        head = fh.read(84)
        if len(head) == 84:
            n = struct.unpack_from("<I", head, 80)[0]
            if n and size == 84 + 50 * n:
                data = fh.read(50 * n)
                unpack = struct.unpack_from
                tris = []
                append = tris.append
                for i in range(n):
                    v = unpack("<9f", data, i * 50 + 12)
                    append(v)
                return tris
        fh.seek(0)
        raw = fh.read().decode("utf-8", "ignore")

    tris = []
    cur = []
    for line in raw.splitlines():
        line = line.strip()
        if line[:6].lower() == "vertex":
            p = line.split()
            cur.append(float(p[1]))
            cur.append(float(p[2]))
            cur.append(float(p[3]))
            if len(cur) == 9:
                tris.append(tuple(cur))
                cur = []
    return tris


def read_obj(path):
    """Le um OBJ (vertices + faces) e devolve triangulos no formato do STL."""
    verts = []
    tris = []
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for line in fh:
            if line[:2] == "v ":
                p = line.split()
                verts.append((float(p[1]), float(p[2]), float(p[3])))
            elif line[:2] == "f ":
                idx = [int(tok.split("/")[0]) for tok in line.split()[1:]]
                if len(idx) < 3:
                    continue
                for i in range(1, len(idx) - 1):
                    tri = []
                    for k in (idx[0], idx[i], idx[i + 1]):
                        k = k - 1 if k > 0 else len(verts) + k
                        tri.extend(verts[k])
                    tris.append(tuple(tri))
    return tris


def read_mesh(path):
    if os.path.splitext(path)[1].lower() == ".obj":
        return read_obj(path)
    return read_stl(path)


# ------------------------------------------------------------------ render


def render(tris, width=800, height=600, az=38.0, el=26.0, max_tris=160000,
           base=(105, 148, 200), bg_top=(255, 255, 255), bg_bottom=(228, 236, 246)):
    n = len(tris)
    if n == 0:
        raise ValueError("malha vazia")
    if n > max_tris:
        step = int(math.ceil(n / float(max_tris)))
        tris = tris[::step]

    # --- base da camera: azimuth/elevacao, mundo com Z para cima
    a, e = math.radians(az), math.radians(el)
    # vetor do centro para a camera
    cx = math.cos(e) * math.sin(a)
    cy = -math.cos(e) * math.cos(a)
    cz = math.sin(e)
    # vetor "direita" da tela
    rx, ry, rz = math.cos(a), math.sin(a), 0.0
    # vetor "cima" da tela = camera x direita
    ux = cy * rz - cz * ry
    uy = cz * rx - cx * rz
    uz = cx * ry - cy * rx

    pts = []
    for t in tris:
        v = []
        for k in range(0, 9, 3):
            x, y, z = t[k], t[k + 1], t[k + 2]
            v.append((x * rx + y * ry + z * rz,        # tela X
                      x * ux + y * uy + z * uz,        # tela Y (para cima)
                      x * cx + y * cy + z * cz))       # profundidade (maior = mais perto)
        pts.append(v)

    minx = miny = 1e30
    maxx = maxy = -1e30
    for v in pts:
        for (px, py, _d) in v:
            if px < minx:
                minx = px
            if px > maxx:
                maxx = px
            if py < miny:
                miny = py
            if py > maxy:
                maxy = py

    dw = maxx - minx or 1.0
    dh = maxy - miny or 1.0
    margin = 0.08
    scale = min((width * (1 - 2 * margin)) / dw, (height * (1 - 2 * margin)) / dh)
    ox = width / 2.0 - (minx + dw / 2.0) * scale
    oy = height / 2.0 + (miny + dh / 2.0) * scale      # tela Y cresce para baixo

    # --- luz no espaco de visao (vinda de cima/esquerda, levemente da frente)
    lx, ly, lz = -0.45, 0.58, 0.68
    ll = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ll, ly / ll, lz / ll

    faces = []
    for v in pts:
        (ax, ay, ad), (bx, by, bd), (cx2, cy2, cd) = v
        v1x, v1y, v1z = bx - ax, by - ay, bd - ad
        v2x, v2y, v2z = cx2 - ax, cy2 - ay, cd - ad
        nx = v1y * v2z - v1z * v2y
        ny = v1z * v2x - v1x * v2z
        nz = v1x * v2y - v1y * v2x
        nl = math.sqrt(nx * nx + ny * ny + nz * nz)
        if nl < 1e-12:
            continue
        nx, ny, nz = nx / nl, ny / nl, nz / nl
        if nz < 0:                       # normal virada para o espectador
            nx, ny, nz = -nx, -ny, -nz
        d = abs(nx * lx + ny * ly + nz * lz)
        shade = 0.34 + 0.62 * (d ** 0.85)
        shade += 0.09 * (d ** 20)        # brilho especular suave
        r = int(min(255, base[0] * shade))
        g = int(min(255, base[1] * shade))
        b = int(min(255, base[2] * shade))
        depth = (ad + bd + cd) / 3.0
        faces.append((depth, (ax * scale + ox, oy - ay * scale,
                              bx * scale + ox, oy - by * scale,
                              cx2 * scale + ox, oy - cy2 * scale), (r, g, b)))

    faces.sort(key=lambda f: f[0])       # mais longe primeiro

    # --- fundo com gradiente vertical suave
    sup = 2 if len(faces) <= 90000 else 1
    W, H = width * sup, height * sup
    img = Image.new("RGB", (W, H), bg_top)
    dr = ImageDraw.Draw(img)
    for yy in range(H):
        k = yy / float(max(1, H - 1))
        dr.line([(0, yy), (W, yy)], fill=(int(bg_top[0] + (bg_bottom[0] - bg_top[0]) * k),
                                          int(bg_top[1] + (bg_bottom[1] - bg_top[1]) * k),
                                          int(bg_top[2] + (bg_bottom[2] - bg_top[2]) * k)))
    for _d, poly, col in faces:
        if sup != 1:
            poly = [c * sup for c in poly]
        dr.polygon(poly, fill=col)
    if sup != 1:
        img = img.resize((width, height), Image.LANCZOS)
    return img



# ------------------------------------------------------------------ main

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    src, dst = sys.argv[1], sys.argv[2]
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 900
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 675

    tris = read_stl(src)
    img = render(tris, w, h)
    img.save(dst, "PNG", optimize=True)
    print("OK %s -> %s (%d triangulos)" % (os.path.basename(src), dst, len(tris)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
