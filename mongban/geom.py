"""Bố trí bản vẽ (toạ độ giấy) và tính khối lượng thép theo hình học - chuyển từ MONG_BAN_KHONG_SUON.lsp."""
from __future__ import annotations

import math

from .model import SLOPE_DRAW

KGM = {6: 0.222, 8: 0.395, 10: 0.617, 12: 0.888, 14: 1.21, 16: 1.58, 18: 2.0, 20: 2.47,
       22: 2.98, 25: 3.85, 28: 4.83, 32: 6.31, 36: 7.99, 40: 9.86, 50: 15.42}
NPIER = 4   # số thân trụ


def ceil_(x):
    return int(x) + 1 if x > int(x) + 1e-6 else int(x)


def kg(d, tot):
    a = KGM.get(int(d + 0.5))
    return tot * (a if a else d * d / 162.0)


class Geo:
    """Toàn bộ kích thước bố trí (mm giấy) của 1 móng, như các biến mb:* trong Lisp."""

    def __init__(self, p: dict):
        self.p = p
        self.layout()

    def g(self, k):
        return self.p[k]

    # ------------------------------------------------------------------
    def layout(self):
        p = self.p
        l, b, l1, l2 = p["L"], p["B"], p["L1"], p["L2"]
        h1, h2, hb, hv = p["H1"], p["H2"], p["HB"], p["HV"]
        bb, tl, ml, mpl, mpit, hc = p["BB"], p["TL"], p["ML"], p["MPL"], p["MPIT"], p["HC"]
        sl = SLOPE_DRAW
        self.den = int(p["SCALE"] + 0.5)
        k = self.k = 1000.0 / self.den
        self.hasCushion = hc > 1e-6
        self.hL = k * l / 2
        self.hLot = k * (l / 2 + ml)
        self.hPit = k * (l / 2 + mpit)
        self.hPitTop = self.hPit + k * sl * (h1 + tl + hc)
        self.hPl = k * ((l1 + bb) / 2 + mpl)
        self.hPy = k * ((l2 + bb) / 2 + mpl)
        self.dx = k * l1 / 2
        self.dy = k * l2 / 2
        self.ph = k * bb / 2
        self.hB = k * b / 2
        self.hLotY = k * (b / 2 + ml)
        self.cx = max(100.2, 78.0 + self.hPitTop)
        self.ytop = 262.2
        self.ybase = self.ytop - k * (h1 + h2)
        self.ygl = self.ybase + k * h1
        self.ypl = self.ybase + k * hb
        self.yed = self.ybase + k * hv
        self.ylt = self.ybase - k * tl
        self.ylb = self.ylt - k * hc
        self.yd = self.ylb - 10.4
        self.planTop = self.yd - 38.6
        self.planCy = self.planTop - self.hLotY
        self.xgl = self.cx - self.hPitTop
        self.dimX1 = self.xgl - 21.0
        self.dimX2 = self.xgl - 13.2
        # tờ chi tiết
        self.cx2 = max(100.2, 44.0 + self.hLot)
        self.ylt2 = self.ybase - k * tl
        self.planTop2 = self.ylt2 - 45.0
        self.planCy2 = self.planTop2 - self.hLotY

    # ---- tiện ích bố trí thép (toạ độ giấy tính từ tim, cx tuỳ tờ) ------
    def offs(self, ln, s):
        n = 1 + max(1, ceil_(ln / s - 1e-6))
        sa = ln / (n - 1)
        return [self.k * sa * (i - (n - 1) / 2.0) for i in range(n)]

    def offs_top(self, ln, pm, s):
        k = self.k
        hl = ln / 2.0
        out = []
        if pm >= hl - 1e-6:
            nf = max(1, ceil_(ln / s))
            sf = ln / nf
            out = [k * (-hl + (j + 0.5) * sf) for j in range(nf)]
        else:
            nf = max(1, ceil_(2 * pm / s))
            sf = 2 * pm / nf
            ns = max(1, ceil_((hl - pm) / s))
            ss = (hl - pm) / ns
            out += [k * -(pm + (j - 0.5) * ss) for j in range(ns, 0, -1)]
            out += [k * (-pm + (j + 0.5) * sf) for j in range(nf)]
            out += [k * (pm + (j - 0.5) * ss) for j in range(1, ns + 1)]
        return out

    def offs_ch(self, ln):
        s5 = self.g("RB_CH_S") / 1000.0
        return self.offs(max(s5, ln - 2 * s5), s5)

    def rbar(self, key):
        return max(0.12, 0.5 * self.k * self.g(key) / 1000.0)

    def slope_top(self):
        return (self.ypl - self.yed) / (self.hL - self.hPl)

    def ytopc(self, ax, off, depth):
        sl = self.slope_top()
        return min(self.ypl - off, self.ypl - sl * (ax - self.hPl) - off * math.sqrt(1 + sl * sl)) - depth

    def xpk(self, off):
        sl = self.slope_top()
        return self.hPl - off * (math.sqrt(1 + sl * sl) - 1) / sl

    def hook_top(self):
        return (self.yed - self.ybase) / self.k - self.g("COVER") - self.g("COVER_B") - \
            (self.g("RB_TOP_D") + self.g("RB_BOT_D")) / 1000.0

    def bar_span(self):
        """Chiều dài rải thép bản móng theo X (m) dùng cho mặt cắt."""
        rd = max(self.rbar("RB_BOT_D"), self.rbar("RB_TOP_D"))
        return self.g("L") - 2 * self.g("COVER") - 2 * rd / self.k

    # ---- đai cổ móng ---------------------------------------------------
    def hoop_hp(self):
        return ((self.ytop - self.k * self.g("COVER")) - self.ypl) / self.k

    def hoop_n(self, s):
        return 1 + max(1, ceil_(self.hoop_hp() / s))

    def hoop_ys(self):
        n = self.hoop_n(self.g("RT_S") / 1000.0)
        y0 = self.ytop - self.k * self.g("COVER")
        y1 = self.ypl
        return [y0 - i * (y0 - y1) / (n - 1) for i in range(n)]

    def m_bars(self):
        return 1 + int(self.g("RC_N") / 4.0)

    def tie_idx(self):
        m = self.m_bars()
        w = 1000.0 * (self.g("BB") - 2 * self.g("COVER"))
        if m <= 2 or (w <= 400.0 and m <= 4):
            return []
        s = w / (m - 1)
        g = max(1, min(2, int(400.0 / s)))
        lst, i = [], 0
        while i <= (m - 1) / 2.0:
            lst.append(i)
            i += g
        res = []
        for j in lst:
            if j not in res:
                res.append(j)
            if (m - 1 - j) not in res:
                res.append(m - 1 - j)
        res.sort()
        extra, cur = [], res[0]
        for nx in res[1:]:
            while nx - cur > g:
                cur += g
                extra.append(cur)
            cur = nx
        res = sorted(set(res + extra))
        return sorted({j for j in res if 0 < j < m - 1})

    def tie_plan(self):
        ti = self.tie_idx()
        m = self.m_bars()
        runs, cur = [], []
        for j in ti:
            if cur and j == cur[-1] + 1:
                cur.append(j)
            else:
                if cur:
                    runs.append(cur)
                cur = [j]
        if cur:
            runs.append(cur)
        grp, st = None, []
        for run in runs:
            if grp is None and len(run) >= 2 and (m - 1 - run[0]) in run:
                c = len(run) if len(run) <= 3 else (2 if len(run) % 2 == 0 else 3)
                off = (len(run) - c) // 2
                grp = run[off:off + c]
                st += [j for j in run if j not in grp]
            else:
                st += run
        return grp, sorted(st)

    def oct_dim(self):
        grp = self.tie_plan()[0]
        m = self.m_bars()
        kk = 40.0
        r = max(0.35, 0.5 * self.g("RC_D") / 1000.0 * kk)
        hb = kk * (self.g("BB") / 2 - self.g("COVER")) - 0.2 - r
        rt = r + 0.12
        s = 2 * hb / (m - 1)
        return ((max(grp) - (m - 1) / 2.0) * s + 0.41421356 * rt) / kk, (hb + rt) / kk

    # ---- khối lượng thép ------------------------------------------------
    @staticmethod
    def pairs(xs):
        out = {}
        for x in xs:
            key = int(1000.0 * abs(x) + 0.5)
            out[key] = out.get(key, 0) + 1
        return sorted(out.items())

    @staticmethod
    def tbar(a, pa, la, pb, lb, e, hbm, hvm):
        u = max(0.0, (a - pa) / (la - pa))
        b = pb + u * (lb - pb)
        ve = (e - pb) / (lb - pb)
        dz = (hbm - hvm) * max(0.0, ve - u)
        d = math.hypot(e - b, dz)
        return 2 * b, d

    def calc_top(self, pos):
        k = self.k
        lm, bm, c = self.g("L"), self.g("B"), self.g("COVER")
        hbm, hvm = (self.ypl - self.ybase) / k, (self.yed - self.ybase) / k
        px, lx, py, ly = self.hPl / k, self.hL / k, self.hPy / k, self.hB / k
        dia, s = self.g("RB_TOP_D"), self.g("RB_TOP_S") / 1000.0
        hk = 0.1 * ceil_(self.hook_top() / 0.1)
        if pos == 2:
            ps = self.pairs([v / k for v in self.offs_top(lm - 2 * c, px, s)])
        else:
            ps = self.pairs([v / k for v in self.offs_top(bm - 2 * c, py, s)])
        rows, n, tot, sd, sf = [], 0, 0.0, 0.0, 0.0
        for idx, (key, cnt) in enumerate(ps, 1):
            ax = key / 1000.0
            if pos == 2:
                flat, d = self.tbar(ax, px, lx, py, ly, bm / 2 - c, hbm, hvm)
            else:
                flat, d = self.tbar(ax, py, ly, px, lx, lm / 2 - c, hbm, hvm)
            if d < 0.06:
                flat, d = 2 * ((bm / 2 - c) if pos == 2 else (lm / 2 - c)), 0.0
            ln = flat + 2 * d + 2 * hk
            rows.append([idx, dia, 1000 * flat, 1000 * d, 1000 * hk, 1000 * ln, cnt, cnt * ln, kg(dia, cnt * ln)])
            n += cnt
            tot += cnt * ln
            sd += cnt * d
            sf += cnt * flat
        summary = dict(pos=pos, dia=dia, len=1000 * tot / n, qty=str(n), tot=tot, kg=kg(dia, tot),
                       dims=[1000 * sd / n, 1000 * sf / n, 1000 * hk, 1000 * hk])
        return rows, summary

    def calc_kl(self):
        """Bảng thống kê thép (cho 01 móng). Mỗi dòng: dict(pos, dia, len, qty, tot, kg, dims)."""
        k = self.k
        g = self.g
        lm, bm, c, cb = g("L"), g("B"), g("COVER"), g("COVER_B")
        hbm, hvm = (self.ypl - self.ybase) / k, (self.yed - self.ybase) / k
        px, lx, py, ly = self.hPl / k, self.hL / k, self.hPy / k, self.hB / k
        dt, db = g("RB_TOP_D") / 1000.0, g("RB_BOT_D") / 1000.0
        rows = []
        R = lambda pos, dia, ln, qty, tot, dims: rows.append(
            dict(pos=pos, dia=dia, len=ln, qty=qty, tot=tot, kg=kg(dia, tot), dims=dims))
        # 1, 3: lớp dưới
        dia = g("RB_BOT_D")
        n = len(self.offs_top(lm - 2 * c, px, g("RB_BOT_S") / 1000.0))
        R(1, dia, 1000 * (bm - 2 * c), str(n), n * (bm - 2 * c), [1000 * (bm - 2 * c)])
        b2, s2 = self.calc_top(2)
        rows.append(s2)
        n = len(self.offs_top(bm - 2 * c, py, g("RB_BOT_S") / 1000.0))
        R(3, dia, 1000 * (lm - 2 * c), str(n), n * (lm - 2 * c), [1000 * (lm - 2 * c)])
        b4, s4 = self.calc_top(4)
        rows.append(s4)
        # 5: thép chống
        s5 = g("RB_CH_S") / 1000.0
        xs = [v / k for v in self.offs(max(s5, lm - 2 * c - 2 * s5), s5)]
        ys = [v / k for v in self.offs(max(s5, bm - 2 * c - 2 * s5), s5)]
        hkc = 0.1
        n, tot, g5 = 0, 0.0, {}
        for x in xs:
            for y in ys:
                u = max(0.0, (abs(x) - px) / (lx - px))
                v = max(0.0, (abs(y) - py) / (ly - py))
                h = hbm - (hbm - hvm) * max(u, v)
                leg = h - c - cb - dt - db
                n += 1
                tot += leg + 2 * hkc
                key = int(1000 * leg + 0.5)
                g5[key] = g5.get(key, 0) + 1
        b5 = []
        for i, (key, cnt) in enumerate(sorted(g5.items(), reverse=True), 1):
            ln = key / 1000.0 + 2 * hkc
            b5.append([i, g("RB_CH_D"), float(key), 100.0, 100.0, 1000 * ln, cnt, cnt * ln, kg(g("RB_CH_D"), cnt * ln)])
        R(5, g("RB_CH_D"), 1000 * tot / n, str(n), tot, [1000 * hkc, 1000 * hkc])
        # 6: thép chủ cổ móng
        ytb = self.ytop - k * c
        ybb = self.ybase + k * cb + 2 * k * g("RB_BOT_D") / 1000.0
        vert = (ytb - ybb) / k
        n = NPIER * int(g("RC_N"))
        R(6, g("RC_D"), 1000 * (vert + 0.3), f"{int(g('RC_N'))}x{NPIER}", n * (vert + 0.3), [300.0, 1000 * vert])
        # 7: đai
        side = g("BB") - 2 * c
        n7 = self.hoop_n(g("RT_S") / 1000.0)
        R(7, g("RT_D"), 1000 * (4 * side + 0.12), f"{n7}x{NPIER}", n7 * NPIER * (4 * side + 0.12), [60.0, 1000 * side])
        # 9: đai phụ thẳng; 10: đai bát giác
        grp, st = self.tie_plan()
        n9 = self.hoop_n(g("RP_S") / 1000.0)
        if st:
            n = n9 * 2 * len(st) * NPIER
            R(9, g("RP_D"), 1000 * (side + 0.12), f"{n9 * 2 * len(st)}x{NPIER}", n * (side + 0.12), [60.0, 1000 * side, 60.0])
        if grp:
            a, f = self.oct_dim()
            ln = 8 * a + 4 * math.sqrt(2) * (f - a) + 0.12
            R(10, g("RP_D"), 1000 * ln, f"{n9}x{NPIER}", n9 * NPIER * ln, [2000 * a, 1414.2136 * (f - a), 60.0])
        # 11: lưới thép đầu trụ
        hh = g("BB") / 2 - c
        nn = 1 + ceil_(2 * hh / (g("RL_S") / 1000.0))
        n = int(g("RL_N")) * 2 * nn * NPIER
        R(11, g("RL_D"), 2000 * hh, str(n), n * 2 * hh, [2000 * hh])
        # phân loại theo đường kính
        cls = {}
        for r in rows:
            a = cls.setdefault(r["dia"], [0.0, 0.0])
            a[0] += r["tot"]
            a[1] += r["kg"]
        self.kl = rows
        self.klc = sorted((d, v[0], v[1]) for d, v in cls.items())
        self.klb = {2: b2, 4: b4, 5: b5}
        self.seq = {r["pos"]: i for i, r in enumerate(rows, 1)}
        return rows

    def sq(self, num) -> str:
        """Số vị trí hiển thị liên tục 1..n."""
        try:
            return str(self.seq.get(int(num), num))
        except (ValueError, AttributeError):
            return str(num)
