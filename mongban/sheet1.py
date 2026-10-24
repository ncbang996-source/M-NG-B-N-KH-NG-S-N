"""Tờ 1: hình thức móng - mặt cắt A-A, mặt bằng, kích thước, bảng tổng kê (mọi giai đoạn)."""
from __future__ import annotations

import math

from . import model
from .cad import Ctx, txtw
from .geom import Geo

T_SOIL = "ĐẤT THỪA ĐẮP LẠI"
T_AXIS = "TIM MÓNG"
T_CUSHION = "ĐỆM CÁT - DÀY "
T_GEO = "VẢI ĐỊA KỸ THUẬT"
T_ROUTE = "HƯỚNG TUYẾN"
T_BISECT = "HƯỚNG PHÂN GIÁC"
T_PLAN = "MẶT BẰNG MÓNG"


def fx(x, n):
    return f"{abs(x):.{n}f}"


# ---------------------------------------------------------------------------
# ký hiệu dùng chung (cả 2 tờ)
def elev(c: Ctx, x, y, s):
    """Ký hiệu cao độ."""
    c.pl("CHU", False, [(x, y), (x + 2.2, y + 2.4), (x, y + 2.4), (x - 2.1, y + 2.4), (x, y), (x, y + 4.7), (x - 8.0, y + 4.7)])
    c.ln("CHU", x + 4.4, y, x - 4.3, y)
    c.tx("CHU", x - 8.0, y + 5.5, 2.0, s)


def sym(c: Ctx, x, y):
    """Ký hiệu đối xứng: 2 nét mảnh cắt nhau + 2 móc dày ở đầu trên (gốc = giao điểm)."""
    for s in (-1.0, 1.0):
        c.ln("CHU", x + s * 2.836, y - 2.226, x - s * 3.817, y + 2.996)
        c.pl("CHU", False, [(x - s * 3.817, y + 2.996), (x - s * 5.699, y + 0.599)], width=0.5)


def marker(c: Ctx, mx, my, sgn, txt, tx, mlen=7.76):
    """Ký hiệu mặt cắt: thanh đậm + mũi tên hướng lên + chữ."""
    c.rect("MAT CAT", min(mx, mx + sgn * mlen), my - 0.4, max(mx, mx + sgn * mlen), my)
    xa = mx + sgn * (mlen - 2.4)
    c.ln("MAT CAT", xa, my - 6.36, xa, my - 2.36)
    c.arrow("MAT CAT", xa, my - 2.36, xa, my - 0.4, 1.96, 0.8)
    c.tx("CHU", tx, my - 5.5, 4.0, txt)


def marker_a(c: Ctx, mx, my, sgn):
    marker(c, mx, my, sgn, "A", mx + 0.35 if sgn > 0 else mx - 3.2)


def vee(c: Ctx, x1, y1, x2, y2):
    """Mũi tên chữ V tại (x2, y2)."""
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy)
    if d < 1e-9:
        return
    ux, uy = dx / d, dy / d
    bx, by = x2 - ux * 1.2, y2 - uy * 1.2
    c.pl("CHU", False, [(x1, y1), (x2, y2), (bx - uy * 1.6, by + ux * 1.6), (x2, y2), (bx + uy * 1.6, by - ux * 1.6)])


def bolts_plan(c: Ctx, g: Geo, px, py):
    """Cụm 4 bu lông neo nhìn từ trên (khoảng cách theo cổ móng)."""
    o = 0.47 * g.ph
    r = max(0.3, 0.12 * g.ph)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = px + sx * o, py + sy * o
            c.ci("CHU", x, y, r)
            c.ln("CHU", x - 1.8 * r, y, x + 1.8 * r, y)
            c.ln("CHU", x, y - 1.8 * r, x, y + 1.8 * r)


def title(c: Ctx, x, y, s, scale_txt):
    """Tên hình (gạch chân, cao 4) + tỷ lệ bên dưới, canh giữa tại x."""
    c.txj("CHU", x, y, 4.0, s, 1, underline=True)
    c.txj("CHU", x, y - 4.5, 2.0, scale_txt, 1)


# ---------------------------------------------------------------------------
def draw_section(c: Ctx, g: Geo):
    p = g.p
    cx, k = g.cx, g.k
    h1, h2 = p["H1"], p["H2"]
    # bê tông móng
    c.ln("MAIN", cx - g.hL, g.ybase, cx - g.hL, g.yed)
    c.ln("MAIN", cx - g.hL, g.yed, cx - g.hPl, g.ypl)
    c.ln("MAIN", cx - g.hPl, g.ypl, cx + g.hPl, g.ypl)
    c.ln("MAIN", cx + g.hPl, g.ypl, cx + g.hL, g.yed)
    c.ln("MAIN", cx + g.hL, g.yed, cx + g.hL, g.ybase)
    c.ln("MAIN", cx - g.hL, g.yed, cx + g.hL, g.yed)
    c.ln("MAIN", cx - g.hL, g.ybase, cx + g.hL, g.ybase)
    # bê tông lót (nét mảnh)
    c.rect("HINH THUC", cx - g.hLot, g.ylt, cx + g.hLot, g.ybase)
    # cổ móng
    for s in (-1, 1):
        xc = cx + s * g.dx
        c.ln("MAIN", xc - g.ph, g.ypl, xc - g.ph, g.ytop)
        c.ln("MAIN", xc + g.ph, g.ypl, xc + g.ph, g.ytop)
        c.ln("MAIN", xc - g.ph, g.ytop, xc + g.ph, g.ytop)
    # mặt đất, hố đào
    c.ln("HINH THUC", cx - g.hPitTop - 8.0, g.ygl, cx - g.dx - g.ph, g.ygl)
    c.ln("HINH THUC", cx - g.dx + g.ph, g.ygl, cx + g.dx - g.ph, g.ygl)
    c.ln("HINH THUC", cx + g.dx + g.ph, g.ygl, cx + g.hPitTop + 8.0, g.ygl)
    c.ln("HINH THUC", cx - g.hPit, g.ylb, cx - g.hPitTop, g.ygl)
    c.ln("HINH THUC", cx + g.hPit, g.ylb, cx + g.hPitTop, g.ygl)
    c.ln("HINH THUC", cx - g.hPit, g.ylb, cx + g.hPit, g.ylb)
    # hatch bê tông lót
    c.hatch("HATCH", [(cx - g.hLot, g.ylt), (cx + g.hLot, g.ylt), (cx + g.hLot, g.ybase), (cx - g.hLot, g.ybase)],
            "AR-CONC", 0.375)
    if g.hasCushion:
        draw_cushion(c, g)
    # trục
    for s in (-1, 1):
        c.ln("TRUC", cx + s * g.dx, g.ytop + 4.3, cx + s * g.dx, g.ylb - 2.2)
    c.ln("TRUC", cx, g.ylb - 1.5, cx, g.ytop + 4.4)
    sym(c, cx, g.ytop - 0.5)
    ybt = section_bolts(c, g)
    xb = cx + g.dx + 0.47 * g.ph + 1.1
    yb = (g.ytop + ybt) / 2
    c.ln("CHU", xb, yb, xb + 6.0, yb)
    c.tx("CHU", xb + 7.0, yb - 0.8, 1.6, g.p["BLN"])
    # cao độ
    elev(c, g.dimX2 - 17.4, g.ybase, f"-{fx(h1, 2)}m")
    elev(c, g.dimX2 - 17.4, g.ygl, "%%p0.00")
    elev(c, g.dimX2 - 5.4, g.ytop, f"+{fx(h2, 2)}m")
    # đất đắp
    pa = g.ygl + 3.1
    sx, rx = cx - g.hL, cx + g.hL
    xa = min(sx + 3.2, cx - g.dx - g.ph - 0.5)
    c.ln("HINH THUC", sx, g.ygl, xa, pa)
    c.ln("HINH THUC", xa, pa, cx - g.dx - g.ph, pa)
    c.ln("HINH THUC", cx - g.dx + g.ph, pa, cx + g.dx - g.ph, pa)
    c.ln("HINH THUC", rx, g.ygl, 2 * cx - xa, pa)
    c.ln("HINH THUC", 2 * cx - xa, pa, cx + g.dx + g.ph, pa)
    xl = cx - g.dx - g.ph - 2.8
    c.pl("CHU", False, [(xl, g.ygl + 1.4), (xl - 5.6, g.ygl + 5.6), (xl - 32.1, g.ygl + 5.6)])
    c.arrow("CHU", xl - 5.6, g.ygl + 5.6, xl, g.ygl + 1.4, 1.6, 0.4)
    c.tx("CHU", xl - 32.2, g.ygl + 6.4, 2.0, T_SOIL)
    title(c, cx, g.yd - 6.9, "A-A", f"TL:1/{g.den}")


BOLT_GAP = 0.05    # khe hở thực tế giữa vòng đệm / đai ốc và mặt trên cổ móng (m)


def bolt_side(c: Ctx, g: Geo, xb, ytop):
    """Bu lông neo nhìn ngang: thân + vòng đệm + 2 đai ốc, đặt cách mặt cổ móng 1 khe hở."""
    gp = max(0.8, g.k * BOLT_GAP)
    c.rect("CHU", xb - 0.3, ytop, xb + 0.3, ytop + 3.4 + gp)
    for x0, y0, x1, y1 in ((-1.1, 0, 1.1, 0.25), (-0.8, 0.25, 0.8, 1.15), (-0.8, 1.45, 0.8, 2.35)):
        c.rect("CHU", xb + x0, ytop + gp + y0, xb + x1, ytop + gp + y1)
    return ytop + gp + 3.4


def section_bolts(c: Ctx, g: Geo, cx=None):
    cx = g.cx if cx is None else cx
    top = g.ytop
    for s in (-1, 1):
        for t in (-1, 1):
            top = bolt_side(c, g, cx + s * g.dx + t * 0.47 * g.ph, g.ytop)
    return top


def draw_cushion(c: Ctx, g: Geo):
    cx, k, hc, s = g.cx, g.k, g.p["HC"], model.SLOPE_DRAW
    yv = g.ylt
    xw = cx - g.hPit - k * s * hc
    xf = cx - g.hL + 0.5 * k
    lbl = f"{T_CUSHION}{int(1000 * hc + 0.5)}mm"
    yl = (g.ylt + g.ylb) / 2 - 1.0
    wl = txtw(lbl, 2.0) / 2 + 0.8
    hole = [(cx - wl, yl - 1.6), (cx + wl, yl - 1.6), (cx + wl, yl + 1.6), (cx - wl, yl + 1.6)]
    c.hatch("HATCH", [(cx - g.hPit, g.ylb), (cx + g.hPit, g.ylb), (2 * cx - xw, g.ylt), (xw, g.ylt)], "AR-SAND", 1.2,
            holes=[hole] if 2 * 1.6 < (g.ylt - g.ylb) else ())
    c.pl("VAI DIA", False, [(xf + 1.3, yv - 1.3), (xf, yv), (xw, yv), (cx - g.hPit, g.ylb), (cx + g.hPit, g.ylb),
                            (2 * cx - xw, yv), (2 * cx - xf, yv), (2 * cx - xf - 1.3, yv - 1.3)])
    c.txc("CHU", cx, yl, 2.0, lbl)
    xg = cx + 0.3 * g.hPit
    c.pl("CHU", False, [(xg, g.ylb), (xg - 3.5, g.ylb - 4.0), (xg - 3.5 - 25.0, g.ylb - 4.0)])
    c.tx("CHU", xg - 3.5 - 25.0, g.ylb - 3.2, 2.0, T_GEO)


def dim_section(c: Ctx, g: Geo):
    cx, k, hc, s = g.cx, g.k, g.p["HC"], model.SLOPE_DRAW
    w100 = txtw("100", 2.0)
    xr1 = cx - g.hPit - (k * s * (hc + g.p["TL"]) if g.hasCushion else 0.0)
    c.dimV("DIM", (g.xgl - 3.0, g.ygl), (g.xgl - 2.0, g.ybase), g.dimX1)                       # H1
    c.dimV("DIM", (cx - g.hL, g.yed), (cx - g.hLot, g.ybase), xr1 - 14.8)                     # hv
    c.dimV("DIM", (cx - g.hLot, g.ybase), (cx - g.hPl, g.ypl), g.dimX2, (g.dimX2 - 2.0, g.ypl - 0.6))   # hb
    c.dimV("DIM", (cx - g.hPl, g.ypl), (g.xgl - 3.0, g.ygl), g.dimX2)                         # H1 - hb
    c.dimV("DIM", (g.xgl - 3.0, g.ygl), (g.xgl - 4.5, g.ytop), g.dimX2)                       # H2
    xd = xr1 - 4.5
    xpb = cx - (g.hPit + k * s * hc if g.hasCushion else g.hPit)
    if g.hasCushion:
        # dày lót: chữ đưa lên trên, kéo dài đường kích thước tới chữ (tránh chồng với chữ đệm cát)
        yt = g.ybase + 1.0 + w100 / 2
        c.dimV("DIM", (cx - g.hLot, g.ybase), (xpb, g.ylt), xd, (xd - 2.0, yt))
        c.ln("DIM", xd, g.ybase, xd, g.ybase + 1.0 + w100)
        c.dimV("DIM", (cx - g.hPit - k * s * hc, g.ylt), (cx - g.hPit, g.ylb), xd)            # đệm cát
    else:
        c.dimV("DIM", (cx - g.hLot, g.ybase), (xpb, g.ylt), xd)
    # kích thước ngang dưới mặt cắt
    c.dimH("DIM", (cx - g.hL, g.ybase + 1.2), (cx + g.hL, g.ybase + 1.2), g.yd)               # L
    c.dimH("DIM", (cx + g.hL, g.ybase - 4.2), (cx + g.hLot, g.ylt), g.yd, (cx + g.hLot - 0.5, g.yd - 4.5))  # lót phải
    c.dimH("DIM", (cx - g.hL, g.ybase), (cx - g.hLot, g.ybase), g.yd, (cx - g.hLot + 0.5, g.yd - 4.5))      # lót trái
    c.dimH("DIM", (cx - g.hLot, g.ybase), (cx - g.hPit, g.ylb), g.yd, (cx - g.hPit - 3.2, g.yd + 1.7))      # mép hố trái
    c.dimH("DIM", (cx + g.hLot, g.ybase), (cx + g.hPit, g.ylb), g.yd, (cx + g.hPit + 3.2, g.yd + 1.7))      # mép hố phải
    if g.hasCushion:
        c.dimH("DIM", (cx - g.hL, g.ylt), (cx - g.hL + 0.5 * k, g.ylt), g.ylb - 5.0)
        c.dimH("DIM", (cx + g.hL - 0.5 * k, g.ylt), (cx + g.hL, g.ylt), g.ylb - 5.0)
    dim_pier(c, g, cx)


def dim_pier(c: Ctx, g: Geo, cx, xmax_left=None):
    """Vát quanh cổ móng, bề rộng cổ móng, khoảng cách tim (chung cho 2 tờ).
    xmax_left: chữ kích thước vát bên trái phải nằm bên trái hoành độ này (tránh leader)."""
    c.dimH("DIM", (cx + g.hPl, g.ypl), (cx + g.dx + g.ph, g.ypl), g.ypl + 4.9, (cx + g.hPl + 3.2, g.ypl + 6.1))
    xt = cx - g.hPl - 3.6
    if xmax_left is not None:
        w = txtw("100", 2.0)
        if xt + w / 2 > xmax_left:
            xt = xmax_left - w / 2
            c.ln("DIM", xt + w / 2, g.ypl + 4.9, cx - g.hPl - 1.0, g.ypl + 4.9)   # kéo dài đường kích thước tới chữ
    c.dimH("DIM", (cx - g.hPl, g.ypl), (cx - g.dx - g.ph, g.ypl), g.ypl + 4.9, (xt, g.ypl + 6.1))
    c.dimH("DIM", (cx - g.dx - g.ph, g.ytop), (cx - g.dx + g.ph, g.ytop), g.ytop + 6.0)
    c.dimH("DIM", (cx + g.dx - g.ph, g.ytop), (cx + g.dx + g.ph, g.ytop), g.ytop + 6.0)
    c.dimH("DIM", (cx - g.dx, g.ytop + 4.3), (cx + g.dx, g.ytop + 4.3), g.ytop + 12.9)


# ---------------------------------------------------------------------------
def draw_route(c: Ctx, g: Geo, cx, cy):
    ht = int(g.p["HT"])
    lh = g.hB - 1.0
    wr = txtw(T_ROUTE, 2.0)
    if ht == 1:
        dlt = math.radians(10.0)
        sn, cs = math.sin(dlt), math.cos(dlt)
        vee(c, cx, cy, cx + lh * sn, cy + lh * cs)
        vee(c, cx, cy, cx + lh * sn, cy - lh * cs)
        # chữ song song mũi tên, nằm bên phải, không chạm mũi tên và chữ "HƯỚNG PHÂN GIÁC"
        a = max(4.6 + wr / 2, min(0.5 * lh, lh - 2.4 - wr / 2))
        c.txr("CHU", cx + a * sn + 2.4 * cs, cy + a * cs - 2.4 * sn, 2.0, T_ROUTE, 90.0 - 10.0)
        vee(c, cx, cy, cx + g.hL - 1.0, cy)
        c.tx("CHU", cx + 6.0, cy + 1.2, 2.0, T_BISECT)
    elif ht == 2:
        vee(c, cx, cy, cx, cy - lh)
        c.txr("CHU", cx + 2.4, cy - 0.5 * lh, 2.0, T_ROUTE, 90.0)
    else:
        vee(c, cx, cy, cx, cy - lh)
        vee(c, cx, cy, cx, cy + lh)
        c.txr("CHU", cx + 2.4, cy + max(1.5 + wr / 2, min(0.5 * lh, lh - 2.4 - wr / 2)), 2.0, T_ROUTE, 90.0)


def plan_outline(c: Ctx, g: Geo, cx, cy, bolts=True):
    c.rect("HINH THUC", cx - g.hLot, cy - g.hLotY, cx + g.hLot, cy + g.hLotY)
    c.rect("MAIN", cx - g.hL, cy - g.hB, cx + g.hL, cy + g.hB)
    c.rect("MAIN", cx - g.hPl, cy - g.hPy, cx + g.hPl, cy + g.hPy)
    for sx in (-1, 1):
        for sy in (-1, 1):
            c.ln("MAIN", cx + sx * g.hPl, cy + sy * g.hPy, cx + sx * g.hL, cy + sy * g.hB)
            px, py = cx + sx * g.dx, cy + sy * g.dy
            c.rect("MAIN", px - g.ph, py - g.ph, px + g.ph, py + g.ph)
            if bolts:
                bolts_plan(c, g, px, py)
    c.rect("TRUC", cx - g.dx, cy - g.dy, cx + g.dx, cy + g.dy)
    c.ln("TRUC", cx - g.hPl - 0.2, cy, cx + g.hPl + 0.2, cy)
    c.ln("TRUC", cx, cy - g.hPy - 2.0, cx, cy + g.hPy + 2.0)
    marker_a(c, cx - g.hLot - 24.0, cy, 1.0)
    marker_a(c, cx + g.hLot + 23.5, cy, -1.0)


def draw_plan(c: Ctx, g: Geo):
    cx, cy = g.cx, g.planCy
    plan_outline(c, g, cx, cy)
    c.ci("CHU", cx, cy, 1.2)
    c.pl("CHU", False, [(cx, cy), (cx - 3.0, cy - 4.7), (cx - 17.4, cy - 4.7)])
    c.tx("CHU", cx - 17.7, cy - 3.8, 2.0, T_AXIS)
    draw_route(c, g, cx, cy)
    title(c, cx, cy - g.hLotY - 22.8, T_PLAN, f"TL:1/{g.den}")


def dim_plan(c: Ctx, g: Geo, cx, cy, lot=True):
    w100 = txtw("100", 2.0)
    xdl = cx - g.hLot - 7.9
    yt = cy + g.hLotY + 6.0
    yb = cy - g.hLotY - 8.5
    xr = cx + g.hLot + 8.5
    px = cx - g.dx - g.ph
    if lot:   # kích thước lót: chữ đưa ra ngoài để không bị đường gióng cắt
        c.dimV("DIM", (cx - g.hLot, cy + g.hLotY), (cx - g.hL, cy + g.hB), xdl, (xdl - 2.0, cy + g.hLotY + 1.0 + w100 / 2))
    c.dimV("DIM", (cx - g.hL, cy + g.hB), (px, cy + g.dy), xdl)
    c.dimV("DIM", (px, cy + g.dy), (px, cy - g.dy), xdl)
    c.dimV("DIM", (px, cy - g.dy), (cx - g.hL, cy - g.hB), xdl)
    if lot:
        c.dimV("DIM", (cx - g.hL, cy - g.hB), (cx - g.hLot, cy - g.hLotY), xdl, (xdl - 2.0, cy - g.hLotY - 1.0 - w100 / 2))
    c.dimH("DIM", (cx - g.hL, cy + g.hB), (cx - g.dx, cy + g.dy + g.ph), yt)
    c.dimH("DIM", (cx - g.dx, cy + g.dy + g.ph), (cx + g.dx, cy + g.dy + g.ph), yt)
    c.dimH("DIM", (cx + g.dx, cy + g.dy + g.ph), (cx + g.hL, cy + g.hB), yt)
    c.dimH("DIM", (cx - g.hL, cy - g.hB), (cx + g.hL, cy - g.hB), yb)
    if lot:
        c.dimH("DIM", (cx - g.hL, cy - g.hB), (cx - g.hLot, cy - g.hLotY), yb, (cx - g.hLot - 1.0 - w100 / 2, yb + 2.0))
        c.dimH("DIM", (cx + g.hL, cy - g.hB), (cx + g.hLot, cy - g.hLotY), yb, (cx + g.hLot + 1.0 + w100 / 2, yb + 2.0))
    c.dimV("DIM", (cx + g.hL, cy + g.hB), (cx + g.hL, cy - g.hB), xr)


# ---------------------------------------------------------------------------
def draw_summary(c: Ctx, g: Geo):
    p = g.p
    cls = [x for x in g.klc if x[2] > 1e-6]
    tot = sum(x[2] for x in cls)
    cols = [(p["BTM"], "(m3)", 15.0, f"{model.vol_mong(p):.2f}"),
            (p["BTL"], "(m3)", 15.0, f"{model.vol_lot(p):.2f}")]
    for d, _, w in cls:
        cols.append((f"%%C{int(d + 0.5)}", "(kg)", 15.0, f"{w:.2f}"))
    if cls:
        cols.append(("TỔNG K.LƯỢNG", "THÉP (kg)", 21.0, f"{tot:.2f}"))
    if g.hasCushion:
        cols.append(("K.LƯỢNG", "ĐỆM CÁT (m3)", 21.0, f"{model.vol_cat(p):.2f}"))
        cols.append(("DIỆN TÍCH", "VẢI ĐỊA (m2)", 21.0, f"{model.area_vai(p):.2f}"))
    cols.append(("BULONG", "NEO", 18.0, model.bolt_text(p)))
    w = sum(x[2] for x in cols)
    hh, rh, xr, y0 = 12.0, 8.0, 395.0, 267.0
    x0 = xr - w
    c.txj("BANG", x0 + w / 2, y0 + 1.6, 2.2, "BẢNG TỔNG KÊ KHỐI LƯỢNG CHO 01 VỊ TRÍ MÓNG", 1, underline=True)
    for y in (y0, y0 - hh, y0 - hh - rh):
        c.ln("BANG", x0, y, xr, y)
    xs = x0
    c.ln("BANG", xs, y0, xs, y0 - hh - rh)
    for col in cols:
        xs += col[2]
        c.ln("BANG", xs, y0, xs, y0 - hh - rh)
    xs = x0
    for col in cols:
        xm = xs + col[2] / 2
        c.txc("BANG", xm, y0 - 4.0, 1.5, col[0])
        c.txc("BANG", xm, y0 - 8.5, 1.5, col[1])
        c.txc("BANG", xm, y0 - hh - 4.0, 1.8, col[3])
        xs += col[2]


def draw_note(c: Ctx, text):
    x = min(195.0, 261.0 - txtw(text, 2.0))      # không lấn sang khung tên
    c.tx("CHU", x, 26.0, 3.5, "GHI CHÚ", underline=True)
    c.tx("CHU", x, 20.5, 2.0, text)


def draw(c: Ctx, g: Geo):
    if not getattr(g, "kl", None):
        g.calc_kl()
    draw_section(c, g)
    dim_section(c, g)
    draw_plan(c, g)
    dim_plan(c, g, g.cx, g.planCy)
    draw_summary(c, g)
    draw_note(c, "- CHI TIẾT XEM BẢN VẼ SỐ: " + str(g.p.get("CODE", "")))
