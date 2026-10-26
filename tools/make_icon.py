"""Vẽ biểu tượng app: móng bản 3D (bản móng có mặt vát, 4 cổ trụ, bu lông), nhìn trục đo."""
import math
import os

from PIL import Image, ImageDraw

SS = 8                 # vẽ to rồi thu nhỏ để mịn
SIZE = 48
W = SIZE * SS * 2
C30, S30 = math.cos(math.radians(30)), math.sin(math.radians(30))
K = W / 10.8           # đơn vị -> pixel
OX, OY = W / 2, W * 0.7


def P(x, y, z):
    """Trục đo: x sang phải-xuống, y sang trái-xuống, z lên."""
    return (OX + (x - y) * C30 * K, OY + ((x + y) * S30 - z) * K)


def shade(base, f):
    return tuple(max(0, min(255, int(c * f))) for c in base) + (255,)


CON = (205, 208, 212)
EDGE = (88, 92, 100, 255)

# Phương án màu: nền (2 màu gradient hoặc None), bê tông lót, bản móng, cổ trụ, bu lông, viền
THEMES = {
    "goc":    dict(bg=None, lot=(150, 150, 150), slab=CON, pier=CON, bolt=(40, 40, 40), edge=EDGE),
    "xanh":   dict(bg=((30, 64, 175), (56, 189, 248)), lot=(250, 204, 21), slab=(226, 232, 240),
                   pier=(249, 115, 22), bolt=(220, 38, 38), edge=(30, 41, 59, 255)),
    "cam":    dict(bg=((234, 88, 12), (251, 191, 36)), lot=(120, 113, 108), slab=(241, 245, 249),
                   pier=(37, 99, 235), bolt=(30, 41, 59), edge=(30, 41, 59, 255)),
    "khoi":   dict(bg=None, lot=(250, 204, 21), slab=(20, 184, 166), pier=(249, 115, 22),
                   bolt=(220, 38, 38), edge=(15, 23, 42, 255)),
    "la":     dict(bg=((4, 120, 87), (52, 211, 153)), lot=(253, 224, 71), slab=(226, 232, 240),
                   pier=(59, 130, 246), bolt=(220, 38, 38), edge=(20, 30, 40, 255)),
}


def poly(d, pts, col):
    d.polygon([P(*p) for p in pts], fill=col, outline=T["edge"], width=max(1, int(0.55 * SS)))


def box(d, x0, y0, z0, x1, y1, z1, col):
    poly(d, [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], shade(col, 0.80))   # mặt trước-trái
    poly(d, [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], shade(col, 0.62))   # mặt trước-phải
    poly(d, [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], shade(col, 1.06))   # mặt trên


T = THEMES["la"]


def background(side, c0, c1):
    """Ô vuông bo góc, gradient chéo từ c0 (trên-trái) sang c1 (dưới-phải)."""
    g = Image.new("RGBA", (side, side))
    px = g.load()
    for j in range(side):
        for i in range(side):
            t = (i + j) / (2 * side - 2)
            px[i, j] = tuple(int(a + (b - a) * t) for a, b in zip(c0, c1)) + (255,)
    m = Image.new("L", (side, side), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, side - 1, side - 1], radius=side // 5, fill=255)
    out = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(g, (0, 0), m)
    return out


def render(theme="la", size=SIZE):
    global T
    T = THEMES[theme]
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    L, hv, hb = 3.0, 0.32, 0.62           # nửa cạnh bản móng, cao mép, cao giữa
    CON = T["slab"]
    box(d, -L - 0.25, -L - 0.25, -0.22, L + 0.25, L + 0.25, 0.0, T["lot"])          # bê tông lót
    box(d, -L, -L, 0.0, L, L, hv, CON)                                             # bản móng (phần mép)
    p = 1.9                                                                         # nửa cạnh mặt trên phẳng
    poly(d, [(-L, L, hv), (L, L, hv), (p, p, hb), (-p, p, hb)], shade(CON, 0.92))   # vát trước-trái
    poly(d, [(L, -L, hv), (L, L, hv), (p, p, hb), (p, -p, hb)], shade(CON, 0.74))   # vát trước-phải
    poly(d, [(-L, -L, hv), (L, -L, hv), (p, -p, hb), (-p, -p, hb)], shade(CON, 1.10))
    poly(d, [(-L, -L, hv), (-L, L, hv), (-p, p, hb), (-p, -p, hb)], shade(CON, 1.02))
    poly(d, [(-p, -p, hb), (p, -p, hb), (p, p, hb), (-p, p, hb)], shade(CON, 1.08))
    a, hc, H = 1.3, 0.45, 3.9            # tim trụ, nửa cạnh cổ, cao cổ
    for x, y in ((-a, -a), (a, -a), (-a, a), (a, a)):                                # sau trước, trái phải
        box(d, x - hc, y - hc, hb, x + hc, y + hc, H, T["pier"])
        for bx, by in ((-0.2, -0.2), (0.2, -0.2), (-0.2, 0.2), (0.2, 0.2)):
            cx, cy = x + bx, y + by
            x0, y0 = P(cx, cy, H)
            x1, y1 = P(cx, cy, H + 0.45)
            d.line([(x0, y0), (x1, y1)], fill=T["bolt"] + (255,), width=int(1.1 * SS))
    bb = im.getbbox()                                  # cắt sát hình rồi đặt giữa ô vuông có lề
    im = im.crop(bb)
    if T["bg"]:
        side = int(max(im.width, im.height) * 1.22)
        sq = background(side, *T["bg"])
        sq.alpha_composite(im, ((side - im.width) // 2, (side - im.height) // 2))
    else:
        side = int(max(im.width, im.height) * 1.04)
        sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    return sq.resize((size, size), Image.LANCZOS)


def main(out, theme="la"):
    im = render(theme)
    im.save(out, format="ICO", sizes=[(SIZE, SIZE)])
    im.save(os.path.splitext(out)[0] + ".png")


if __name__ == "__main__":
    import sys
    main(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.ico"),
         sys.argv[1] if len(sys.argv) > 1 else "la")
