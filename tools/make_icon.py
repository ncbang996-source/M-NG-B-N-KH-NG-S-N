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


def poly(d, pts, col):
    d.polygon([P(*p) for p in pts], fill=col, outline=EDGE, width=max(1, int(0.55 * SS)))


def box(d, x0, y0, z0, x1, y1, z1, col):
    poly(d, [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], shade(col, 0.80))   # mặt trước-trái
    poly(d, [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], shade(col, 0.62))   # mặt trước-phải
    poly(d, [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], shade(col, 1.06))   # mặt trên


def main(out):
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    L, hv, hb = 3.0, 0.32, 0.62           # nửa cạnh bản móng, cao mép, cao giữa
    box(d, -L - 0.25, -L - 0.25, -0.22, L + 0.25, L + 0.25, 0.0, (150, 150, 150))   # bê tông lót
    box(d, -L, -L, 0.0, L, L, hv, CON)                                             # bản móng (phần mép)
    p = 1.9                                                                         # nửa cạnh mặt trên phẳng
    poly(d, [(-L, L, hv), (L, L, hv), (p, p, hb), (-p, p, hb)], shade(CON, 0.92))   # vát trước-trái
    poly(d, [(L, -L, hv), (L, L, hv), (p, p, hb), (p, -p, hb)], shade(CON, 0.74))   # vát trước-phải
    poly(d, [(-L, -L, hv), (L, -L, hv), (p, -p, hb), (-p, -p, hb)], shade(CON, 1.10))
    poly(d, [(-L, -L, hv), (-L, L, hv), (-p, p, hb), (-p, -p, hb)], shade(CON, 1.02))
    poly(d, [(-p, -p, hb), (p, -p, hb), (p, p, hb), (-p, p, hb)], shade(CON, 1.08))
    a, hc, H = 1.3, 0.45, 3.9            # tim trụ, nửa cạnh cổ, cao cổ
    for x, y in ((-a, -a), (a, -a), (-a, a), (a, a)):                                # sau trước, trái phải
        box(d, x - hc, y - hc, hb, x + hc, y + hc, H, CON)
        for bx, by in ((-0.2, -0.2), (0.2, -0.2), (-0.2, 0.2), (0.2, 0.2)):
            cx, cy = x + bx, y + by
            x0, y0 = P(cx, cy, H)
            x1, y1 = P(cx, cy, H + 0.45)
            d.line([(x0, y0), (x1, y1)], fill=(40, 40, 40, 255), width=int(1.1 * SS))
    bb = im.getbbox()                                  # cắt sát hình rồi đặt giữa ô vuông có lề
    im = im.crop(bb)
    side = int(max(im.width, im.height) * 1.04)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    im = sq.resize((SIZE, SIZE), Image.LANCZOS)
    im.save(out, format="ICO", sizes=[(SIZE, SIZE)])
    im.save(os.path.splitext(out)[0] + ".png")


if __name__ == "__main__":
    main(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icon.ico"))
