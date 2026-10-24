"""Tờ 2 (TKBVTC): mặt cắt A-A có cốt thép, mặt bằng thép, mặt cắt 1-1, lưới đầu trụ, các bảng thép."""
from __future__ import annotations

import math

from .cad import Ctx, txtw
from .geom import Geo, ceil_
from .sheet1 import marker, sym, bolts_plan, plan_outline, dim_plan, dim_pier, title, draw_note, note_at, section_bolts

T_TOP = "THÉP LỚP TRÊN"
T_BOT = "THÉP LỚP DƯỚI"
T_CHONG = "THANH CHỐNG"
T_DAI = "THÉP ĐAI"
T_MESH = "LƯỚI THÉP"
T_MESHH = "LƯỚI THÉP ĐẦU TRỤ"
T_TBL = "BẢNG THỐNG KÊ CỐT THÉP (CHO 01 MÓNG)"
T_TBLH = ["VỊ TRÍ", "HÌNH DẠNG VÀ KÍCH THƯỚC (mm)", "%%C(mm)", "CHIỀU DÀI (mm)", "SỐ LƯỢNG",
          "TỔNG C.DÀI (m)", "KL (kg)"]


def ni(x):
    return str(int(x + 0.5))


def phi(d, s):
    return f"%%C{ni(d)}@{ni(s)}"


# ---------------------------------------------------------------------------
# hình học uốn góc
def rcorner(a, p, b, r):
    dx, dy = p[0] - a[0], p[1] - a[1]
    l1 = math.hypot(dx, dy)
    d1x, d1y = dx / l1, dy / l1
    dx, dy = b[0] - p[0], b[1] - p[1]
    l2 = math.hypot(dx, dy)
    d2x, d2y = dx / l2, dy / l2
    cr = d1x * d2y - d1y * d2x
    dt = d1x * d2x + d1y * d2y
    ph = math.atan2(abs(cr), dt)
    tt = r * math.tan(ph / 2)
    return ((p[0] - d1x * tt, p[1] - d1y * tt), (-1 if cr < 0 else 1) * math.tan(ph / 4),
            (p[0] + d2x * tt, p[1] + d2y * tt))


def rounded(pts, closed, r):
    out, bul = [], []
    n = len(pts)
    for i, p in enumerate(pts):
        if not closed and i in (0, n - 1):
            out.append(p)
            bul.append(0.0)
            continue
        t1, bg, t2 = rcorner(pts[(i - 1) % n], p, pts[(i + 1) % n], r)
        out += [t1, t2]
        bul += [bg, 0.0]
    return out, bul


def rpl(c: Ctx, lay, pts, closed, r):
    out, bul = rounded(pts, closed, r)
    c.pl(lay, closed, out, bulges=bul)


def dai_draw(c: Ctx, lay, x0, y0, x1, y1, r, hk):
    """Đai kín bo góc bán kính r, 2 móc 45 độ ở góc dưới phải."""
    rpl(c, lay, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True, r)
    e = r + 0.3
    c.ln(lay, x1, y0 + e, x1 - hk, y0 + e + hk)
    c.ln(lay, x1 - e, y0, x1 - e - hk, y0 + hk)


def shape_dai_cong(c: Ctx, lay, x, y, s):
    pts = [(x + s * a, y + s * b) for a, b in ((0, 0), (1, 0), (1, 1), (0, 1))]
    rpl(c, lay, pts, True, 0.07 * s)
    c.ln(lay, x + s * 1.0, y + s * 0.14, x + s * 0.87, y + s * 0.27)
    c.ln(lay, x + s * 0.86, y, x + s * 0.73, y + s * 0.13)


def shape_chu_u(c: Ctx, lay, x, y, s):
    rpl(c, lay, [(x, y + 0.3 * s), (x, y), (x + s, y), (x + s, y + 0.3 * s)], False, 0.07 * s)


def shape_l2(c: Ctx, lay, x, y, s):
    rpl(c, lay, [(x, y + 0.13 * s), (x, y), (x + s, y)], False, 0.03 * s)


def tie(c: Ctx, lay, x0, y0, ux, uy, ln, r, tl):
    """Thanh đai phụ: thẳng, 2 đầu uốn móc 180 độ."""
    vx, vy = -uy, ux
    tp = lambda a, b: (x0 + a * ux + b * vx, y0 + a * uy + b * vy)
    c.pl(lay, False, [tp(tl, 2 * r), tp(0, 2 * r), tp(0, 0), tp(ln, 0), tp(ln, 2 * r), tp(ln - tl, 2 * r)],
         bulges=[0, 1.0, 0, 1.0, 0, 0])


def tick45(c: Ctx, x, y, fixed=False):
    c.pl("CHU", False, [(x - 0.48, y - 0.48), (x + 0.48, y + 0.48)], width=0.12, fixed=(0, 1) if fixed else ())


def balloon(c: Ctx, x, y, num):
    c.ci("CHU", x, y, 3.0)
    c.txc("CHU", x, y, 2.4, num)


# ---------------------------------------------------------------------------
class Callouts:
    """Chú thích số hiệu thép: các nhánh tới mục tiêu -> đoạn ngang -> vòng tròn số."""

    def __init__(self, c: Ctx, g: Geo):
        self.c, self.g = c, g

    def __call__(self, targets, bx, by, side, num, txt1, txt2=None, tick=True, mode=True):
        with self.c.item(f"callout{num}", f"Chú thích thép {self.g.sq(num)}"):
            return self._draw(targets, bx, by, side, num, txt1, txt2, tick, mode)

    def _anchor(self, me, i, tp):
        """Điểm bắt leader vào thép: cố định theo hình, chỉ dịch khi kéo riêng điểm này (id ...@t<i>)."""
        c = self.c
        if me is None:
            return tp
        from .cad import Obj
        aid = f"{me.id}@t{i}"
        d = c.offsets.get(aid)
        x, y = (tp[0] + d[0], tp[1] + d[1]) if d else tp
        gx, gy = c.off(False)
        a = Obj(aid, "anchor", "Điểm bắt leader")
        a.add(x + gx - 0.9, y + gy - 0.9)
        a.add(x + gx + 0.9, y + gy + 0.9)
        c.objs.append(a)
        return (x, y)

    def _draw(self, targets, bx, by, side, num, txt1, txt2, tick, mode):
        c = self.c
        ln = max(txtw(txt1, 2.0), txtw(txt2, 2.0) if txt2 else 0.0)
        span = 3.0 + 1.3 + ln + 2.5
        bx = bx + side * span                      # bx = điểm bắt đầu đường tag
        ex = bx - side * span
        tx = bx - side * 4.3
        c.ln("CHU", ex, by, bx - side * 3.0, by)
        di = c.item_off()                          # dịch chuyển riêng của tag (leader tự co giãn)
        me = c._stack[-1] if c._stack else None
        for i, tp in enumerate(targets):
            tp = self._anchor(me, i, tp)
            if mode == "hd":
                dr = 1.0 if tp[0] > ex + di[0] else -1.0
                xk = ex + dr * max(2.0, 0.35 * abs(tp[0] - ex - di[0]))
                c.ln("CHU", ex, by, xk, by)
                c.ln("CHU", xk, by, tp[0], tp[1], fixed2=True)
            elif mode:
                xt = tp[0] - di[0]                 # đoạn đứng luôn đi qua đúng thanh thép
                c.ln("CHU", ex, by, xt, by)
                if abs(by + di[1] - tp[1]) > 0.01:
                    c.ln("CHU", xt, by, tp[0], tp[1], fixed2=True)
            else:
                c.ln("CHU", ex, by, tp[0], tp[1], fixed2=True)
            if tick:
                tick45(c, tp[0], tp[1], fixed=True)
        c.txj("CHU", tx, by + 0.8, 2.0, txt1, 2 if side > 0 else 0)
        if txt2:
            c.txj("CHU", tx, by - 2.8, 2.0, txt2, 2 if side > 0 else 0)
        balloon(c, bx, by, self.g.sq(num))
        return min(ex, bx - 3.0), max(ex, bx + 3.0)


def gapx(dots, xr):
    out, prev = xr, None
    for d in dots:
        if prev is not None and prev <= xr < d:
            out = 0.5 * (prev + d)
        prev = d
    return out


def nearx(dots, xr):
    return min(dots, key=lambda d: abs(d - xr))


def prevx(dots, x0):
    best = x0
    for d in dots:
        if d < x0 - 1e-6:
            best = d
    return best


def yg(hb, m, k):
    return -hb + (k + 0.5) * (2 * hb / (m - 1))


# ---------------------------------------------------------------------------
def d2_section(c: Ctx, g: Geo, co: Callouts):
    p = g.p
    cx, k = g.cx2, g.k
    cov = p["COVER"]
    hk = 0.1 * k
    rdb, rdt = g.rbar("RB_BOT_D"), g.rbar("RB_TOP_D")
    rd = max(rdb, rdt)
    # bê tông
    c.ln("MAIN", cx - g.hL, g.ybase, cx - g.hL, g.yed)
    c.ln("MAIN", cx - g.hL, g.yed, cx - g.hPl, g.ypl)
    c.ln("MAIN", cx - g.hPl, g.ypl, cx + g.hPl, g.ypl)
    c.ln("MAIN", cx + g.hPl, g.ypl, cx + g.hL, g.yed)
    c.ln("MAIN", cx + g.hL, g.yed, cx + g.hL, g.ybase)
    c.ln("MAIN", cx - g.hL, g.ybase, cx + g.hL, g.ybase)
    c.rect("HINH THUC", cx - g.hLot, g.ylt2, cx + g.hLot, g.ybase)
    for s in (-1, 1):
        xc = cx + s * g.dx
        c.ln("MAIN", xc - g.ph, g.ypl, xc - g.ph, g.ytop)
        c.ln("MAIN", xc + g.ph, g.ypl, xc + g.ph, g.ytop)
        c.ln("MAIN", xc - g.ph, g.ytop, xc + g.ph, g.ytop)
    for s in (-1, 1):
        c.ln("TRUC", cx + s * g.dx, g.ytop + 4.3, cx + s * g.dx, g.ylt2 - 2.2)
    c.ln("TRUC", cx, g.ylt2 - 1.5, cx, g.ytop + 4.4)
    sym(c, cx, g.ytop - 0.5)
    # thép bản móng
    off, offb = k * cov, k * p["COVER_B"]
    span = g.bar_span()
    yb1, yb3 = g.ybase + offb + rdb, g.ybase + offb + 3 * rdb
    for d in g.offs_top(span, g.hPl / k, p["RB_BOT_S"] / 1000.0):
        c.disc("COTTHEP", cx + d, yb1, rdb)
    xe = g.hL - off - rd
    c.ln("COTTHEP", cx - xe, yb3, cx + xe, yb3)
    hlt = k * g.hook_top()
    for d in g.offs_top(span, g.hPl / k, p["RB_TOP_S"] / 1000.0):
        c.disc("COTTHEP", cx + d, g.ytopc(abs(d), off, rdt), rdt)
    ye = g.ytopc(xe, off, 3 * rdt)
    yp = g.ypl - off - 3 * rdt
    xp = g.xpk(off)
    c.pl("COTTHEP", False, [(cx - xe, ye - hlt), (cx - xe, ye), (cx - xp, yp), (cx + xp, yp), (cx + xe, ye), (cx + xe, ye - hlt)])
    for d in g.offs_ch(span):
        y = g.ytopc(abs(d), off, 3 * rdt)
        xh = min(cx + d + hk, cx + xe)
        c.pl("DAI", False, [(xh, yb3), (cx + d, yb3), (cx + d, y), (xh, y)])
    # thép cổ móng bên phải
    pcx = cx + g.dx
    ytb = g.ytop - off
    ybb = g.ybase + offb + 2 * k * p["RB_BOT_D"] / 1000.0
    foot = 0.3 * k
    xl, xr = pcx - (g.ph - off), pcx + (g.ph - off)
    c.pl("COTTHEP", False, [(xl, ytb), (xl, ybb), (xl - foot, ybb)])     # móc chân quay ra ngoài
    c.pl("COTTHEP", False, [(xr, ytb), (xr, ybb), (xr + foot, ybb)])
    ml, ms, mr = int(p["RL_N"]), k * p["RL_S"] / 1000.0, g.rbar("RL_D")
    hhb = g.ph - off
    for il in range(ml):
        yl = ytb - mr - il * ms
        c.ln("DAI", pcx - hhb, yl, pcx + hhb, yl)
        nd = ceil_(2 * (hhb - mr) / ms)
        for jd in range(nd + 1):
            c.disc("DAI", pcx - (hhb - mr) + jd * 2 * (hhb - mr) / nd, yl - 2 * mr, mr)
    for yy in g.hoop_ys():
        c.ln("DAI", pcx - (g.ph - off), yy, pcx + (g.ph - off), yy)
    # bu lông neo trên đỉnh 2 cổ (thân + vòng đệm + 2 đai ốc, có khe hở)
    section_bolts(c, g, cx)
    yc2 = d2_section_callouts(c, g, co)
    d2_cutmark(c, g, yc2)


def d2_cutmark(c: Ctx, g: Geo, ymin):
    """Ký hiệu mặt cắt 1-1 trên cổ móng trái, đặt cao hơn chú thích thép số 2."""
    pcx = g.cx2 - g.dx
    xl, xr = pcx - g.ph, pcx + g.ph
    yc = max(g.ypl + 0.55 * (g.ytop - g.ypl), ymin)
    yc = min(yc, g.ytop - 2.0)
    marker(c, xl - 2.0, yc, -1.0, "1", xl - 2.0 - 3.0 - 3.2, mlen=5.4)
    marker(c, xr + 2.0, yc, 1.0, "1", xr + 2.0 + 3.0 + 1.4, mlen=5.4)


def d2_section_callouts(c: Ctx, g: Geo, co: Callouts):
    p = g.p
    cx, k = g.cx2, g.k
    cov = p["COVER"]
    off, offb = k * cov, k * p["COVER_B"]
    rdb, rdt = g.rbar("RB_BOT_D"), g.rbar("RB_TOP_D")
    span = g.bar_span()
    bxr = cx + g.hL + 4.0
    bxp = cx + g.dx + g.ph + 6.0
    xt = cx + 0.5 * (g.hPl + g.hL)
    xa = cx + g.dx + g.ph
    # trái: lớp trên (2), thép chống (5), lớp dưới (1)
    dots = g.offs_top(span, g.hPl / k, p["RB_TOP_S"] / 1000.0)
    by2 = g.ypl + 14.6
    co([(cx + dots[1], g.ytopc(abs(dots[1]), off, rdt)), (cx + dots[2], g.ytopc(abs(dots[2]), off, rdt))],
       cx - g.hL + 8.0, by2, -1, "2", phi(p["RB_TOP_D"], p["RB_TOP_S"]), tick=False, mode=False)
    dots = g.offs_ch(span)
    x5 = cx + prevx(dots, nearx(dots, -g.hL + 45.0))
    _, ex5 = co([(x5, (g.ybase + g.ypl) / 2)], cx - g.hL + 30.0, g.ylt2 - 13.0, -1, "5", T_CHONG,
                phi(p["RB_CH_D"], p["RB_CH_S"]), mode=False)
    dots = g.offs_top(span, g.hPl / k, p["RB_BOT_S"] / 1000.0)
    co([(cx + dots[1], g.ybase + offb + rdb), (cx + dots[2], g.ybase + offb + rdb)],
       cx - g.hL - 9.8, g.ylt2 - 7.0, -1, "1", phi(p["RB_BOT_D"], p["RB_BOT_S"]), tick=False, mode=False)
    # phải: lớp dưới theo X (3), lớp trên theo X (4)
    co([(cx + gapx(dots, 0.7 * g.hL), g.ybase + offb + 3 * rdb)], bxr, g.ylt2 - 7.0, 1, "3",
       phi(p["RB_BOT_D"], p["RB_BOT_S"]))
    dots = g.offs_top(span, g.hPl / k, p["RB_TOP_S"] / 1000.0)
    xt = cx + gapx(dots, xt - cx)
    co([(xt, g.ytopc(abs(xt - cx), off, 3 * rdt))], bxr, g.ypl + 4.5, 1, "4", phi(p["RB_TOP_D"], p["RB_TOP_S"]))
    # 11 (lưới đầu trụ): chỉ vào 2 thanh tròn ở 2 lớp lưới
    ytb = g.ytop - off
    ml, ms = int(p["RL_N"]), k * p["RL_S"] / 1000.0
    pcx = cx + g.dx
    mr = g.rbar("RL_D")
    lst = [(pcx + (g.ph - off) - mr, ytb - mr - il * ms - 2 * mr) for il in range(min(2, ml))]
    by11 = lst[0][1]
    co(lst, bxp, by11, 1, "11", T_MESH, phi(p["RL_D"], p["RL_S"]), tick=False, mode=False)
    # 7: đường ngang -> 1 đường dọc qua các lớp đai, có dấu gạch tại 2..4 đai
    hys = g.hoop_ys()
    st = (hys[0] - hys[1]) if len(hys) > 1 else k * p["RT_S"] / 1000.0
    y0 = g.ytop - off - int(p["RL_N"]) * k * p["RL_S"] / 1000.0
    by7 = g.ypl + 11.0
    stv = max(1, ceil_(3.0 / st))
    xv7 = xa - off - 2.0
    i0 = min(range(len(hys)), key=lambda i: abs(hys[i] - by7))
    ys = []
    for j in (-1, 0, 1):
        ii = i0 + j * stv
        if 0 <= ii < len(hys) and g.ypl + off + 1.0 <= hys[ii] <= y0:
            ys.append(hys[ii])
    if len(ys) < 2:
        ys = [by7 + st, by7 - st]
    with c.item("callout7", f"Chú thích thép {g.sq(7)}"):
        co([], bxp, by7, 1, "7", T_DAI, phi(p["RT_D"], p["RT_S"]))
        di = c.item_off()
        c.ln("CHU", bxp, by7, xv7 + di[0], by7, fixed2=False)
        c.ln("CHU", xv7, min([by7] + ys), xv7, max([by7] + ys), fixed1=True, fixed2=True)
        c.ln("CHU", xv7, by7 + di[1], xv7 + di[0], by7 + di[1], fixed1=True, fixed2=True)
        for y in ys:
            tick45(c, xv7, y, fixed=True)
    # 6: 1 đường ngang chỉ vào 2 thanh chủ (giữa 2 đai), cách các chú thích 7 và 11 đủ xa
    y6 = None
    for j in range(len(hys) - 1):
        ym = 0.5 * (hys[j] + hys[j + 1])
        if g.ypl + 23.0 <= ym <= ytb - ml * ms - 2.0 and ym <= by11 - 7.5 and ym >= by7 + 7.5:
            y6 = ym
    if y6 is None:
        y6 = min(ytb - ml * ms - 4.0, by11 - 7.5)
    co([(pcx + (g.ph - off), y6), (pcx - (g.ph - off), y6)], bxp, y6, 1, "6",
       f"{ni(p['RC_N'])}%%C{ni(p['RC_D'])}", mode=True)
    # tên hình: dời sang phải nếu chú thích số 5 lấn tới
    w = txtw("A-A", 4.0)
    xt = max(cx, ex5 + 3.0 + w / 2)
    title(c, xt, g.ylt2 - 15.8, "A-A", f"TL:1/{g.den}")
    return by2 + 9.5


def d2_dim_section(c: Ctx, g: Geo):
    cx = g.cx2
    yd = g.ylt2 - 4.5
    xv = cx - g.hL - 7.0
    c.dimV("DIM", (cx - g.hL, g.yed), (cx - g.hLot, g.ybase), xv)
    c.dimV("DIM", (cx - g.hLot, g.ybase), (cx - g.hPl, g.ypl), xv - 7.0)
    c.dimV("DIM", (cx - g.dx - g.ph, g.ypl), (cx - g.dx - g.ph, g.ytop), cx - g.hL - 14.0)
    c.dimV("DIM", (cx - g.dx - g.ph, g.ybase), (cx - g.dx - g.ph, g.ytop), cx - g.hL - 21.0)
    c.dimH("DIM", (cx - g.hL, g.ybase), (cx + g.hL, g.ybase), yd)
    dim_pier(c, g, cx, xmax_left=cx - g.hL + 8.0 - 2.5)    # bên trái leader thép số 2


# ---------------------------------------------------------------------------
def d2_break(c: Ctx, cx, yh, yl, w):
    ym = (yh + yl) / 2
    hh = 1.15 * w
    c.pl("CHU", False, [(cx - w, yh), (cx - w, ym + hh), (cx - 2 * w, ym + hh), (cx, ym - hh), (cx - w, ym - hh), (cx - w, yl)])
    c.pl("CHU", False, [(cx + w, yh), (cx + w, ym + hh), (cx, ym + hh), (cx + 2 * w, ym - hh), (cx + w, ym - hh), (cx + w, yl)])


def pick(cands, outl, tgt):
    best, bd = None, -1e9
    for cc in cands:
        m = min(abs(abs(cc) - o) for o in outl)
        d = -abs(cc - tgt)
        if m > 1.3 and d > bd:
            best, bd = cc, d
    return best if best is not None else tgt


def d2_plan_bars(c: Ctx, g: Geo, cx, cy):
    p = g.p
    k = g.k
    cov = p["COVER"]
    off = k * cov
    lx, ly = g.hL, g.hB
    ye, ex = ly - off, lx - off
    hk = 0.1 * k
    ox = [g.hPl, g.hL, g.hLot, g.dx, g.dx - g.ph, g.dx + g.ph, 3.0]
    oy = [g.hPy, g.hB, g.hLotY, g.dy, g.dy - g.ph, g.dy + g.ph, 3.0]
    # 1: lớp dưới, dọc theo Y, bên phải
    xs = g.offs_top(p["L"] - 2 * cov, g.hPl / k, p["RB_BOT_S"] / 1000.0)
    g.bx1 = pick([v for v in xs if g.hPl < v < ex], ox, 0.85 * lx)
    c.ln("COTTHEP", cx + g.bx1, cy - ye, cx + g.bx1, cy + ye)
    # 3: lớp dưới, theo X, phía trên
    ys = g.offs_top(p["B"] - 2 * cov, g.hPy / k, p["RB_BOT_S"] / 1000.0)
    g.by3 = pick([v for v in ys if g.hPy < v < ye], oy, 0.88 * ly)
    c.ln("COTTHEP", cx + 1.8, cy + g.by3, cx + ex, cy + g.by3)
    # 2: lớp trên, dọc theo Y, bên trái; 2 đầu uốn xiên về góc rồi móc 100
    xs = g.offs_top(p["L"] - 2 * cov, g.hPl / k, p["RB_TOP_S"] / 1000.0)
    g.bx2 = pick([v for v in xs if -ex < v < -g.hPl], ox, -0.68 * lx)
    cc = g.bx2
    ca = abs(cc)
    sl = (ly - g.hPy) / (lx - g.hPl)
    y1 = g.hPy + sl * (ca - g.hPl)
    sh = max(0.0, min(0.5 * (ye - y1), ex - ca - hk))
    c.pl("COTTHEP", False, [(cx + cc - sh - hk, cy - ye), (cx + cc - sh, cy - ye), (cx + cc, cy - y1),
                            (cx + cc, cy + y1), (cx + cc - sh, cy + ye), (cx + cc - sh - hk, cy + ye)])
    # 4: lớp trên, theo X, phía dưới
    ys = g.offs_top(p["B"] - 2 * cov, g.hPy / k, p["RB_TOP_S"] / 1000.0)
    g.by4 = pick([v for v in ys if -ye < v < -g.hPy], oy, -0.58 * ly)
    cc = abs(g.by4)
    sl = (lx - g.hPl) / (ly - g.hPy)
    x1 = g.hPl + sl * (cc - g.hPy)
    y2 = min(ye - hk, cc + 0.5 * (ex - x1))
    y3 = y2 + hk
    g.t4x, g.t4y = -min(x1 - 0.5, g.hPl + 1.2), -cc
    c.pl("COTTHEP", False, [(cx - 1.8, cy + g.by4), (cx - x1, cy + g.by4), (cx - ex, cy - y2), (cx - ex, cy - y3)])


def d2_plan(c: Ctx, g: Geo, co: Callouts):
    p = g.p
    cx, cy = g.cx2, g.planCy2
    plan_outline(c, g, cx, cy)
    d2_plan_bars(c, g, cx, cy)
    d2_break(c, cx, cy + g.hLotY + 2.0, cy - g.hLotY - 2.0, 1.8)
    bxl, bxr = cx - g.hLot - 15.0, cx + g.hLot + 12.0
    co([(cx + g.bx2, cy + 0.3 * g.hB)], bxl, cy + 0.3 * g.hB, -1, "2", phi(p["RB_TOP_D"], p["RB_TOP_S"]))
    co([(cx + g.t4x, cy - abs(g.t4y))], bxl, cy - g.hLotY - 4.8, -1, "4", phi(p["RB_TOP_D"], p["RB_TOP_S"]))
    co([(cx + g.bx1, cy + 0.3 * g.hB)], bxr, cy + 0.3 * g.hB, 1, "1", phi(p["RB_BOT_D"], p["RB_BOT_S"]))
    co([(cx + 0.75 * g.hL, cy + g.by3)], bxr, cy + 0.62 * g.hB, 1, "3", phi(p["RB_BOT_D"], p["RB_BOT_S"]))
    ybot = cy - g.hLotY
    c.txj("CHU", cx - 0.5 * g.hL, ybot - 14.2, 2.0, T_TOP, 1, underline=True)
    c.txj("CHU", cx + 0.5 * g.hL, ybot - 14.2, 2.0, T_BOT, 1, underline=True)
    title(c, cx, ybot - 26.8, "MẶT BẰNG MÓNG", f"TL:1/{g.den}")


# ---------------------------------------------------------------------------
def dim25(c: Ctx, cx, cy, hh):
    from .cad import ensure_dimstyle
    nm = ensure_dimstyle(c.doc, 25)
    c.dimH("DIM", (cx - hh, cy - hh), (cx + hh, cy - hh), cy - hh - 4.5, dimname=nm)
    c.dimV("DIM", (cx - hh, cy - hh), (cx - hh, cy + hh), cx - hh - 4.5, dimname=nm)


def small_title(c: Ctx, cx, cy, hh, s):
    with c.item("title", "Tên hình"):
        _small_title(c, cx, cy, hh, s)


def _small_title(c: Ctx, cx, cy, hh, s):
    c.txj("CHU", cx, cy - hh - 13.0, 4.0, s, 1, underline=True)
    c.txj("CHU", cx, cy - hh - 18.0, 2.0, "1/25", 1)


def d2_sec11(c: Ctx, g: Geo, co: Callouts, cx, cy):
    p = g.p
    kk, cov = 40.0, p["COVER"]
    hh = kk * p["BB"] / 2
    c.rect("MAIN", cx - hh, cy - hh, cx + hh, cy + hh)
    hb = hh - kk * cov
    hb0 = hb
    dai_draw(c, "DAI", cx - hb, cy - hb, cx + hb, cy + hb, 1.0, 1.3)
    n = int(p["RC_N"])
    m = 1 + int(n / 4.0)
    dia = p["RC_D"]
    r = max(0.35, 0.5 * dia / 1000.0 * kk)
    hb = hb - 0.2 - r
    lst = []
    for i in range(m):
        x = -hb + i * 2 * hb / (m - 1)
        lst += [(x, -hb), (x, hb)]
        if 0 < i < m - 1:
            lst += [(-hb, x), (hb, x)]
    for px, py in lst:
        c.disc("COTTHEP", cx + px, cy + py, r)
    grp, st = g.tie_plan()
    rt = r + 0.12
    for i in st:
        x = -hb + i * 2 * hb / (m - 1)
        tie(c, "DAI", cx + x + rt, cy - hb, 0.0, 1.0, 2 * hb, rt, 2.2)
        tie(c, "DAI", cx - hb, cy + x - rt, 1.0, 0.0, 2 * hb, rt, 2.2)
    xo = yo = None
    if grp:
        i = max(grp)
        xo = abs(-hb + i * 2 * hb / (m - 1)) + 0.41421356 * rt
        yo = hb + rt
        c.pl("DAI", True, [(cx - xo, cy + yo), (cx + xo, cy + yo), (cx + yo, cy + xo), (cx + yo, cy - xo),
                           (cx + xo, cy - yo), (cx - xo, cy - yo), (cx - yo, cy - xo), (cx - yo, cy + xo)])
    bx = cx + hh + 5.0
    sp = 2 * hb / (m - 1)
    ng = m - 1
    ds = max(1, ceil_(6.4 / sp))
    k10 = k9 = None
    y10 = y9 = None
    if grp:
        k10 = max(0, min(ng - 1, int(0.5 + (hb - 0.5 * (xo + yo)) / sp - 0.5)))
        y10 = yg(hb, m, k10)
        if abs(y10) < xo + 0.5 or abs(y10) > yo - 0.5:
            y10 = -0.5 * (xo + yo)
            k10 = max(0, min(ng - 1, int((y10 + hb) / sp)))
    k7 = ng - 1
    if st:
        k9 = k7 - ds
    if k10 is not None and k9 is not None and k9 < k10 + ds:
        k9 = k10 + ds
        k7 = max(k7, k9 + ds)
    if k10 is not None and k9 is None and k7 < k10 + ds:
        k7 = k10 + ds
    k7 = max(0, min(ng - 1, k7))
    y7 = yg(hb, m, k7)
    if k9 is not None:
        k9 = max(0, min(ng - 1, k9))
        y9 = yg(hb, m, k9)
    co([(cx - hb + i * sp, cy + hb) for i in range(m)], bx, cy + hh + 6.0, 1, "6", f"{ni(n)}%%C{ni(dia)}", tick=False)
    co([(cx + hb0, cy + y7)], bx, cy + y7, 1, "7", phi(p["RT_D"], p["RT_S"]))
    if st:
        xi = -hb + max(st) * sp
        co([(cx + xi + r + 0.12, cy + y9), (cx, cy + xi - (r + 0.12))], bx, cy + y9, 1, "9", phi(p["RP_D"], p["RP_S"]))
    if grp:
        co([(cx + (xo + yo) - abs(y10), cy + y10)], bx, cy + y10, 1, "10", phi(p["RP_D"], p["RP_S"]))
    dim25(c, cx, cy, hh)
    small_title(c, cx, cy, hh, "1-1")


def d2_mesh(c: Ctx, g: Geo, co: Callouts, cx, cy):
    p = g.p
    kk = 40.0
    hh = kk * p["BB"] / 2
    c.rect("MAIN", cx - hh, cy - hh, cx + hh, cy + hh)
    hb = hh - kk * p["COVER"]
    s = kk * p["RL_S"] / 1000.0
    n = ceil_(2 * hb / s)
    for i in range(n + 1):
        v = -hb + i * 2 * hb / n
        c.ln("DAI", cx - hb, cy + v, cx + hb, cy + v)
        c.ln("DAI", cx + v, cy - hb, cx + v, cy + hb)
    co([(cx + hb, cy + 3.0)], cx + hh + 5.0, cy + 3.0, 1, "11", phi(p["RL_D"], p["RL_S"]), f"({int(p['RL_N'])} LỚP)")
    dim25(c, cx, cy, hh)
    small_title(c, cx, cy, hh, T_MESHH)


# ---------------------------------------------------------------------------
def tbl_lbl(c: Ctx, x, y, s):
    c.txc("BANG", x, y, 1.3, s)


def oct_hook(c: Ctx, lay, vx, vy, p1, p2, cx, cy, hl):
    a = 0.2094
    for pt in (p1, p2):
        d = math.hypot(pt[0] - vx, pt[1] - vy)
        u = ((pt[0] - vx) / d, (pt[1] - vy) / d)
        nrm = (-u[1], u[0])
        if nrm[0] * (cx - vx) + nrm[1] * (cy - vy) < 0:
            nrm = (-nrm[0], -nrm[1])
        c.ln(lay, vx, vy, vx + hl * (u[0] * math.cos(a) - nrm[0] * math.sin(a)),
             vy + hl * (u[1] * math.cos(a) - nrm[1] * math.sin(a)))


def tbl_shape(c: Ctx, pos, d, ln, x, y, w, h):
    yc, xm, lay = y + h / 2, x + w / 2, "BANG"
    if pos in (1, 3, 11):
        c.ln(lay, x + 3, yc, x + w - 3, yc)
        tbl_lbl(c, xm, yc + 1.6, ni(ln))
    elif pos in (2, 4):
        yt = y + h - 3.0
        yb = yt - 1.6
        sl, x0, x1 = 6.0, x + 8.0, x + w - 8.0
        c.pl(lay, False, [(x0, yb - 1.6), (x0, yb), (x0 + sl, yt), (x1 - sl, yt), (x1, yb), (x1, yb - 1.6)])
        tbl_lbl(c, xm, yt + 1.2, ni(d[1]))
        tbl_lbl(c, x0 + 2.4, yb + 1.7, ni(d[0]))
        tbl_lbl(c, x0 - 1.8, yb - 0.8, ni(d[2]))
        tbl_lbl(c, x1 + 1.8, yb - 0.8, ni(d[3]))
    elif pos == 5:
        x0 = xm - 6.3
        shape_chu_u(c, lay, x0, y + 2.8, 12.6)
        tbl_lbl(c, xm, y + 1.4, ni(ln - d[0] - d[1]))
        tbl_lbl(c, x0 - 3.5, y + 5.0, ni(d[0]))
        tbl_lbl(c, x0 + 16.1, y + 5.0, ni(d[1]))
    elif pos == 6:
        x0, x1 = x + 4.0, x + w - 4.0
        shape_l2(c, lay, x0, y + 2.4, x1 - x0)
        tbl_lbl(c, xm + 2.0, y + 4.0, ni(d[1]))
        tbl_lbl(c, x0 + 3.4, y + h - 2.4, ni(d[0]))
    elif pos == 7:
        shape_dai_cong(c, lay, xm - 5.0, y + 2.0, 10.0)
        tbl_lbl(c, xm, y + 12.8, ni(d[1]))
        c.txr("BANG", xm - 6.6, y + 7.0, 1.3, ni(d[1]), 90.0)
        tbl_lbl(c, xm + 8.0, y + 3.2, ni(d[0]))
    elif pos == 10:
        x0 = 4.5 * (0.5 * d[0] / (0.5 * d[0] + d[1] / 1.41421))
        c.pl(lay, True, [(xm - x0, yc + 4.5), (xm + x0, yc + 4.5), (xm + 4.5, yc + x0), (xm + 4.5, yc - x0),
                         (xm + x0, yc - 4.5), (xm - x0, yc - 4.5), (xm - 4.5, yc - x0), (xm - 4.5, yc + x0)])
        oct_hook(c, lay, xm - 4.5, yc + x0, (xm - 4.5, yc - x0), (xm - x0, yc + 4.5), xm, yc, 3.0)
        tbl_lbl(c, xm, yc + 5.3, ni(d[0]))
        tbl_lbl(c, xm + 8.0, yc + 4.4, ni(d[1]))
        tbl_lbl(c, xm - 9.5, yc + x0 - 1.5, ni(d[2]))
    elif pos == 9:
        x0, x1 = x + 0.15 * w + 3.0, x + w - 0.15 * w - 3.0
        tie(c, lay, x0, y + 2.4, 1.0, 0.0, x1 - x0, 0.7, 2.0)
        tbl_lbl(c, xm, y + 5.0, ni(d[1]))
        tbl_lbl(c, x0 - 3.0, y + 2.6, ni(d[0]))
        tbl_lbl(c, x1 + 3.0, y + 2.6, ni(d[2]))


def d2_table(c: Ctx, g: Geo, tx, ty):
    cw = [10.0, 46.0, 10.0, 18.0, 15.0, 18.0, 14.0]
    rh, hh = 8.0, 10.0
    rows = g.kl
    hs = [16.0 if r["pos"] == 7 else 14.0 if r["pos"] == 10 else rh for r in rows]
    th = sum(hs)
    wcol = sum(cw)
    c.txj("BANG", tx, ty + 3.0, 2.5, T_TBL, 0, underline=True)
    c.ln("BANG", tx, ty, tx + wcol, ty)
    c.ln("BANG", tx, ty - hh, tx + wcol, ty - hh)
    for i in range(len(rows)):
        y = ty - hh - sum(hs[:i + 1])
        c.ln("BANG", tx, y, tx + wcol, y)
    xs = tx
    c.ln("BANG", xs, ty, xs, ty - hh - th)
    for w in cw:
        xs += w
        c.ln("BANG", xs, ty, xs, ty - hh - th)
    xs = tx
    for i, w in enumerate(cw):
        c.txc("BANG", xs + w / 2, ty - 5.0, 1.4 if i != 1 else 1.4, T_TBLH[i])
        xs += w
    ssum = 0.0
    for i, r in enumerate(rows):
        rhi = hs[i]
        y = ty - hh - sum(hs[:i + 1])
        ym = y + rhi / 2
        ssum += r["kg"]
        c.txc("BANG", tx + 5.0, ym, 1.8, g.sq(r["pos"]))
        tbl_shape(c, r["pos"], r["dims"], r["len"], tx + 10.0, y, 46.0, rhi)
        c.txc("BANG", tx + 61.0, ym, 1.6, ni(r["dia"]))
        c.txc("BANG", tx + 75.0, ym, 1.6, ni(r["len"]))
        c.txc("BANG", tx + 91.5, ym, 1.6, r["qty"])
        c.txc("BANG", tx + 108.0, ym, 1.6, f"{r['tot']:.2f}")
        c.txc("BANG", tx + 124.0, ym, 1.6, f"{r['kg']:.2f}")
    y = ty - hh - th
    c.ln("BANG", tx, y - 6.0, tx + wcol, y - 6.0)
    c.ln("BANG", tx, y, tx, y - 6.0)
    c.ln("BANG", tx + wcol, y, tx + wcol, y - 6.0)
    c.ln("BANG", tx + 117.0, y, tx + 117.0, y - 6.0)
    c.txj("BANG", tx + 3.0, y - 4.2, 1.6, "CỘNG", 0)
    c.txc("BANG", tx + 124.0, y - 3.4, 1.6, f"{ssum:.2f}")
    return y - 6.0


def bar_shape(c: Ctx, x0, x1, yt, hd, sl, dh):
    c.pl("BANG", False, [(x0, yt - hd - dh), (x0, yt - hd), (x0 + sl, yt), (x1 - sl, yt), (x1, yt - hd), (x1, yt - hd - dh)])
    c.txc("BANG", 0.5 * (x0 + x1), yt + 1.2, 1.0, "L1")
    c.txc("BANG", x0 + 0.6, yt - 0.5 * hd + 0.6, 1.0, "L2")
    c.txc("BANG", x0 - 1.6, yt - hd - 0.5 * dh, 1.0, "L3")


def bar_shape5(c: Ctx, x0, x1, yc):
    yb = yc - 2.0
    c.pl("BANG", False, [(x0, yb + 4.0), (x0, yb), (x1, yb), (x1, yb + 4.0)])
    c.txc("BANG", 0.5 * (x0 + x1), yb - 1.8, 1.0, "L1")
    c.txc("BANG", x0 - 1.8, yb + 2.0, 1.0, "L2")
    c.txc("BANG", x1 + 1.8, yb + 2.0, 1.0, "L3")


def bar_groups(rows, pos):
    out, lastk = [], None
    for r in rows:
        key = (ni(r[2]), ni(r[3]), ni(r[4]), ni(r[5]))
        if key == lastk:
            gg = out[-1]
            gg[5] += r[6]
            gg[6] += r[7]
        else:
            out.append([f"{pos}.{len(out) + 1}", ni(r[2]), ni(r[3]), ni(r[4]), ni(r[5]), r[6], r[7]])
        lastk = key
    return out


def d2_bartable(c: Ctx, g: Geo, tx, ty, pos, ybot=None):
    rows = g.klb.get(pos)
    if not rows:
        return
    cw = [12.0, 19.0, 8.0, 8.0, 7.0, 9.0, 6.0, 10.0]
    wtot = sum(cw)
    grp = bar_groups(rows, pos)
    n = len(grp)
    hh = 11.0
    rh = max(7.0, 15.0 / n)
    if ybot is not None:                     # co chiều cao dòng để bảng không tràn khỏi khung
        rh = max(3.6, min(rh, (ty - hh - ybot) / n))
    c.txj("BANG", tx, ty + 2.4, 1.8, f"BẢNG KÍCH THƯỚC TỪNG THANH SỐ {g.sq(pos)} (mm)", 0, underline=True)
    c.ln("BANG", tx, ty, tx + wtot, ty)
    c.ln("BANG", tx, ty - hh, tx + wtot, ty - hh)
    xw = tx + cw[0]
    x1 = xw + cw[1]
    for i in range(1, n + 1):
        y = ty - hh - i * rh
        c.ln("BANG", tx, y, xw, y)
        c.ln("BANG", x1, y, tx + wtot, y)
    xs = tx
    c.ln("BANG", xs, ty, xs, ty - hh - n * rh)
    for w in cw:
        xs += w
        c.ln("BANG", xs, ty, xs, ty - hh - n * rh)
    c.ln("BANG", xw, ty - hh - n * rh, x1, ty - hh - n * rh)
    xs = tx
    for i, h in enumerate(["THANH", "HÌNH DẠNG", "L1", "L2", "L3", "DÀI", "SL", "TỔNG (m)"]):
        c.txc("BANG", xs + cw[i] / 2, ty - 5.5, 1.2, h)
        xs += cw[i]
    if pos == 5:
        bar_shape5(c, xw + 3.5, x1 - 3.5, ty - hh - 0.5 * n * rh)
    else:
        bar_shape(c, xw + 3.5, x1 - 3.5, ty - hh - 0.5 * n * rh + 4.5, 4.5, 3.5, 3.5)
    for ri, r in enumerate(grp):
        y = ty - hh - (ri + 1) * rh
        ym = y + rh / 2
        # nhãn thanh hiển thị theo số vị trí liên tục
        lbl = f"{g.sq(pos)}.{r[0].split('.')[1]}"
        c.txc("BANG", tx + 6.0, ym, 1.2, lbl)
        xs = x1
        for i, v in enumerate([r[1], r[2], r[3], r[4], ni(r[5]), f"{r[6]:.2f}"], start=2):
            c.txc("BANG", xs + cw[i] / 2, ym, 1.2, v)
            xs += cw[i]


# ---------------------------------------------------------------------------
def draw(c: Ctx, g: Geo):
    if not getattr(g, "kl", None):
        g.calc_kl()
    co = Callouts(c, g)
    with c.group("section", "Mặt cắt A-A (thép)"):
        d2_section(c, g, co)
        d2_dim_section(c, g)
    with c.group("plan", "Mặt bằng thép"):
        d2_plan(c, g, co)
        dim_plan(c, g, g.cx2, g.planCy2, lot=False)
    with c.group("sec11", "Mặt cắt 1-1"):
        d2_sec11(c, g, co, 212.0, 236.0)
    with c.group("mesh", "Lưới thép đầu trụ"):
        d2_mesh(c, g, co, 298.0, 236.0)
    hh = 40.0 * g.p["BB"] / 2
    with c.table("table", "Bảng thống kê cốt thép"):
        ytb = d2_table(c, g, 264.0, min(188.0, 236.0 - hh - 27.0))
    note = "- XEM GHI CHÚ CHUNG TẠI BẢN VẼ SỐ: " + str(g.p.get("CODE", ""))
    yb = g.planCy2 - g.hLotY - 40.0
    if ytb >= 79.0:
        # ghi chú đặt giữa bảng thống kê và khung tên -> bảng kích thước thanh dùng hết chiều cao bên trái
        note_at(c, 266.0, 71.5, note)
        ybot = 13.0
    else:
        draw_note(c, note)
        ybot = 33.0
    for x, pos in ((22.0, 2), (103.0, 4), (184.0, 5)):
        with c.table(f"bar{pos}", f"Bảng kích thước thanh số {g.sq(pos)}"):
            d2_bartable(c, g, x, yb, pos, ybot=ybot)
