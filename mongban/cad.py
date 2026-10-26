"""Lớp vẽ: tạo layer, kiểu chữ, kiểu kích thước và các hàm vẽ cơ bản trên ezdxf (toạ độ giấy, mm)."""
from __future__ import annotations

import math
import os
import sys
from functools import lru_cache

import ezdxf
from ezdxf.enums import TextEntityAlignment

# ---------------------------------------------------------------------------
# Layer: (màu, kiểu đường, độ dày nét x0.01mm)
#   trục 0.13 < kích thước / leader / đường bao thường 0.18 < bao móng 0.30 < đai 0.40 < thép chủ 0.50
LAYERS = {
    "TRUC":      (4, "CENTER", 13),     # trục, tim
    "HATCH":     (8, "CONTINUOUS", 13),  # hatch đệm cát, bê tông lót
    "DIM":       (4, "CONTINUOUS", 18),  # kích thước
    "CHU":       (7, "CONTINUOUS", 18),  # chữ, leader, vòng số hiệu, ký hiệu
    "HINH THUC": (6, "CONTINUOUS", 18),  # mặt đất, hố đào, bê tông lót, đất đắp
    "VAI DIA":   (1, "CONTINUOUS", 30),  # vải địa kỹ thuật (bằng nét bao móng)
    "BANG":      (7, "CONTINUOUS", 18),  # bảng
    "MAIN":      (3, "CONTINUOUS", 30),  # đường bao móng
    "MAT CAT":   (3, "CONTINUOUS", 30),  # ký hiệu mặt cắt
    "DAI":       (2, "CONTINUOUS", 35),  # thép đai, thép phân bố, lưới (mỏng hơn thép chủ)
    "COTTHEP":   (1, "CONTINUOUS", 50),  # thép chủ
}
_SIG = "d9bb90e55bf7014d"
STYLE = "ROBOTO_CONDENSED"
STYLE_B = "ROBOTO_CONDENSED-B"
# Font chữ bản vẽ: đặt đúng tên file như font Roboto Condensed cài trên máy (khung tên SEIAC cũng dùng),
# kèm tên họ font (XDATA) để AutoCAD hiện "Roboto Condensed" trong Text Style.
FONT_R = "Roboto_Condensed-Regular.ttf"
FONT_B = "Roboto_Condensed-Bold.ttf"
FONT_FAMILY = "Roboto Condensed"
WIDTH = 0.8                                # Width Factor của kiểu chữ


def resource_dir() -> str:
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets")


def font_dir() -> str:
    return os.path.join(resource_dir(), "fonts")


_fonts_ready = False


def init_fonts():
    global _fonts_ready
    if _fonts_ready:
        return
    import pathlib
    from ezdxf.fonts import fonts
    fonts.font_manager.scan_folder(pathlib.Path(font_dir()))
    _fonts_ready = True


@lru_cache(maxsize=8)
def _font(name=FONT_R):
    init_fonts()
    from ezdxf.fonts import fonts
    return fonts.make_font(name, 1.0)


def txtw(s: str, h: float, bold=False) -> float:
    """Bề rộng thật của dòng chữ (chiều cao chữ h)."""
    s = s.replace("%%C", "Ø").replace("%%c", "Ø").replace("%%P", "±").replace("%%p", "±")
    try:
        return _font(FONT_B if bold else FONT_R).text_width(s) * h * WIDTH
    except Exception:
        return 0.62 * h * len(s) * WIDTH


def new_doc():
    init_fonts()
    doc = ezdxf.new("R2018", setup=True, units=4)
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LTSCALE"] = 1.0
    doc.header["$PSLTSCALE"] = 0
    doc.header["$LWDISPLAY"] = 1
    ensure_styles(doc)
    for name, (col, lt, lw) in LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, color=col, linetype=lt if lt in doc.linetypes else "CONTINUOUS", lineweight=lw)
    return doc


def ensure_styles(doc):
    """Kiểu chữ ROBOTO_CONDENSED (Regular) và ROBOTO_CONDENSED-B (Bold): Height 0, Width Factor 0.8."""
    for name, f, bold in ((STYLE, FONT_R, False), (STYLE_B, FONT_B, True)):
        st = doc.styles.get(name) if name in doc.styles else doc.styles.new(name)
        st.dxf.font = f
        st.dxf.height = 0.0
        st.dxf.width = WIDTH
        st.dxf.oblique = 0.0
        st.set_extended_font_data(FONT_FAMILY, italic=False, bold=bold)


def ensure_dimstyle(doc, den: int) -> str:
    nm = f"MB{den}"
    if nm in doc.dimstyles:
        return nm
    ds = doc.dimstyles.new(nm)
    a = ds.dxf
    a.dimtxsty = STYLE
    a.dimtxt = 2.0
    a.dimasz = 1.0
    a.dimblk = "ARCHTICK"
    a.dimexo = 1.0
    a.dimexe = 1.0
    a.dimgap = 1.0
    a.dimdli = 7.0
    a.dimdle = 1.0
    a.dimdec = 0
    a.dimtad = 1
    a.dimtih = 0
    a.dimtoh = 0
    a.dimtix = 1
    a.dimtofl = 1
    a.dimlfac = float(den)
    a.dimrnd = 0.1
    a.dimtmove = 2
    a.dimscale = 1.0
    a.dimclrd = 256
    a.dimclre = 256
    a.dimclrt = 256
    a.dimlwd = -1
    a.dimlwe = -1
    return nm


def dot_free(name, scale, dot=0.2):
    """Mẫu hatch chuẩn nhưng chấm (nét dài 0) đổi thành nét ngắn ~dot mm.
    Chấm dài 0 bị một số trình xem PDF / phiên bản thư viện bỏ qua -> mất hatch cát."""
    from ezdxf.tools import pattern
    lines = pattern.ISO_PATTERN.get(name)
    if not lines:
        return None
    d0 = dot / max(scale, 1e-9)
    out = []
    for ang, base, off, dashes in lines:
        nd = []
        for i, v in enumerate(dashes):
            if v == 0.0:
                nd.append(d0)
                if i + 1 < len(dashes) and dashes[i + 1] < 0:
                    dashes = list(dashes)
                    dashes[i + 1] = min(-1e-6, dashes[i + 1] + d0)
            else:
                nd.append(v)
        out.append([ang, base, off, nd])
    return out


class Obj:
    """Đối tượng dịch chuyển được: 'group' (cả hình) hoặc 'item' (chữ, dim, chú thích, bảng...)."""
    __slots__ = ("id", "kind", "label", "bbox")

    def __init__(self, oid, kind, label=""):
        self.id, self.kind, self.label = oid, kind, label
        self.bbox = [1e18, 1e18, -1e18, -1e18]

    def add(self, x, y):
        b = self.bbox
        b[0], b[1], b[2], b[3] = min(b[0], x), min(b[1], y), max(b[2], x), max(b[3], y)

    def ok(self):
        return self.bbox[0] < self.bbox[2] + 1e-9


class Ctx:
    """Vẽ vào modelspace với gốc toạ độ o (góc dưới trái khung tên).

    Dịch chuyển: offsets = {id: (dx, dy)} (mm giấy). Mọi điểm vẽ trong 1 nhóm cộng offset của nhóm;
    điểm của 1 item cộng thêm offset của item, trừ các điểm 'neo' (mũi leader, điểm đo của dim)."""

    def __init__(self, doc, msp, ox=0.0, oy=0.0, den=100, offsets=None, prefix="s1"):
        self.doc, self.msp, self.ox, self.oy = doc, msp, ox, oy
        self.offsets = offsets or {}
        self.prefix = prefix
        self.objs: list[Obj] = []
        self._stack: list[Obj] = []
        self._count: dict = {}
        self.set_scale(den)

    def set_scale(self, den):
        self.den = int(den)
        self.dimname = ensure_dimstyle(self.doc, self.den)

    # --- đối tượng --------------------------------------------------------
    def _new_id(self, name):
        base = self._stack[0].id if self._stack else self.prefix
        oid = f"{base}.{name}"
        n = self._count.get(oid, 0)
        self._count[oid] = n + 1
        return oid if n == 0 else f"{oid}{n + 1}"

    def begin(self, name, kind="item", label=""):
        """Mở 1 đối tượng. Nhóm: name tuyệt đối (vd 'section'); item: tên tương đối trong nhóm."""
        if kind == "group":
            oid = f"{self.prefix}.{name}"
        elif self._stack and (self._stack[-1] is None or self._stack[-1].kind in ("item", "table")):
            self._stack.append(None)      # lồng trong item: không tạo item mới
            return None
        else:
            oid = self._new_id(name)
        o = Obj(oid, kind, label)
        self._stack.append(o)
        return o

    def end(self):
        o = self._stack.pop()
        if o is not None and o.ok():
            self.objs.append(o)
            for p in self._stack:          # cộng bbox vào các đối tượng cha
                if p is not None:
                    p.add(o.bbox[0], o.bbox[1])
                    p.add(o.bbox[2], o.bbox[3])

    class _Scope:
        def __init__(self, c, name, kind, label):
            self.c, self.args = c, (name, kind, label)

        def __enter__(self):
            return self.c.begin(*self.args)

        def __exit__(self, *a):
            self.c.end()

    def group(self, name, label=""):
        return Ctx._Scope(self, name, "group", label)

    def item(self, name, label=""):
        return Ctx._Scope(self, name, "item", label)

    def table(self, name, label=""):
        """Bảng: dịch chuyển nguyên khối, chữ trong bảng không tách riêng."""
        if self._stack:
            return Ctx._Scope(self, name, "item", label)
        return Ctx._Scope(self, name, "table", label)

    def off(self, item=True):
        dx = dy = 0.0
        for o in self._stack:
            if o is None:
                continue
            if o.kind == "item" and not item:
                continue
            d = self.offsets.get(o.id)
            if d:
                dx += d[0]
                dy += d[1]
        return dx, dy

    def wp(self, x, y, item=True):
        dx, dy = self.off(item)
        x, y = x + dx, y + dy
        for o in self._stack:
            if o is not None and (item or o.kind != "item"):   # điểm neo không tính vào khung của item
                o.add(x, y)
        return (self.ox + x, self.oy + y)

    # --- hình học ---------------------------------------------------------
    def ln(self, lay, x1, y1, x2, y2, fixed1=False, fixed2=False):
        return self.msp.add_line(self.wp(x1, y1, not fixed1), self.wp(x2, y2, not fixed2), dxfattribs={"layer": lay})

    def item_off(self):
        """Offset riêng của item đang mở (không tính nhóm)."""
        a, b = self.off(True), self.off(False)
        return a[0] - b[0], a[1] - b[1]

    def pl(self, lay, closed, pts, width=0.0, bulges=None, fixed=()):
        pp = []
        for i, p in enumerate(pts):
            b = bulges[i] if bulges else 0.0
            x, y = self.wp(p[0], p[1], i not in fixed)
            pp.append((x, y, width, width, b))
        return self.msp.add_lwpolyline(pp, format="xyseb", close=closed, dxfattribs={"layer": lay})

    def rect(self, lay, x1, y1, x2, y2):
        return self.pl(lay, True, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)])

    def ci(self, lay, x, y, r):
        self.wp(x - r, y - r)
        self.wp(x + r, y + r)
        return self.msp.add_circle(self.wp(x, y), r, dxfattribs={"layer": lay})

    def disc(self, lay, x, y, r):
        """Chấm tròn đặc bán kính r (polyline bề rộng r)."""
        return self.pl(lay, True, [(x - r / 2, y), (x + r / 2, y)], width=r, bulges=[1.0, 1.0])

    def arrow(self, lay, x1, y1, x2, y2, ln, wid, fixed=False):
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy)
        if d < 1e-9:
            return
        ux, uy = dx / d, dy / d
        bx, by = x2 - ux * ln, y2 - uy * ln
        it = not fixed
        self.msp.add_solid([self.wp(bx - uy * wid, by + ux * wid, it), self.wp(bx + uy * wid, by - ux * wid, it),
                            self.wp(x2, y2, it), self.wp(x2, y2, it)], dxfattribs={"layer": lay})

    def hatch(self, lay, pts, pattern, scale, angle=0.0, holes=()):
        h = self.msp.add_hatch(dxfattribs={"layer": lay})
        if pattern.upper().startswith("AR-"):
            scale = scale / 25.4      # mẫu AR- của AutoCAD (acadiso.pat) không nhân 25.4 như bảng ISO của ezdxf
        h.set_pattern_fill(pattern, scale=scale, angle=angle, definition=dot_free(pattern, scale))
        h.paths.add_polyline_path([self.wp(*p) for p in pts], is_closed=True, flags=1)
        for hp in holes:                       # lỗ (vd. chừa chỗ cho chữ)
            h.paths.add_polyline_path([self.wp(*p) for p in hp], is_closed=True, flags=16)
        return h

    # --- chữ --------------------------------------------------------------
    def _text(self, lay, x, y, h, s, align, rot=0.0, bold=False, underline=False):
        top = self._stack[-1] if self._stack else "none"
        auto = top == "none" or (top is not None and top.kind == "group")
        if auto:                                   # chữ đứng riêng trong nhóm -> 1 item
            self.begin("text", "item", s)
        w = txtw(s, h, bold)
        ox_ = {TextEntityAlignment.LEFT: 0.0, TextEntityAlignment.CENTER: -w / 2,
               TextEntityAlignment.RIGHT: -w}.get(align, -w / 2)
        oy_ = -h / 2 if align == TextEntityAlignment.MIDDLE_CENTER else 0.0
        ca, sa = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        for u, v in ((ox_, oy_ - 0.3 * h), (ox_ + w, oy_ - 0.3 * h), (ox_ + w, oy_ + h), (ox_, oy_ + h)):
            self.wp(x + u * ca - v * sa, y + u * sa + v * ca)
        t = self.msp.add_text(s, height=h, rotation=rot,
                              dxfattribs={"layer": lay, "style": STYLE_B if bold else STYLE, "width": WIDTH})
        t.set_placement(self.wp(x, y), align=align)
        if underline:
            self._underline(lay, x, y, h, s, align, bold)
        if auto:
            self.end()
        return t

    def _underline(self, lay, x, y, h, s, align, bold):
        w = txtw(s, h, bold)
        if align in (TextEntityAlignment.LEFT,):
            x0, yb = x, y
        elif align in (TextEntityAlignment.CENTER,):
            x0, yb = x - w / 2, y
        elif align in (TextEntityAlignment.RIGHT,):
            x0, yb = x - w, y
        else:  # MIDDLE_CENTER
            x0, yb = x - w / 2, y - h / 2
        yu = yb - 0.25 * h
        self.ln(lay, x0, yu, x0 + w, yu)

    def tx(self, lay, x, y, h, s, **kw):
        """Chữ canh trái, điểm đặt trên đường cơ sở."""
        return self._text(lay, x, y, h, s, TextEntityAlignment.LEFT, **kw)

    def txc(self, lay, x, y, h, s, **kw):
        """Chữ canh giữa (giữa theo cả 2 phương)."""
        return self._text(lay, x, y, h, s, TextEntityAlignment.MIDDLE_CENTER, **kw)

    def txr(self, lay, x, y, h, s, rot, **kw):
        return self._text(lay, x, y, h, s, TextEntityAlignment.MIDDLE_CENTER, rot=rot, **kw)

    def txj(self, lay, x, y, h, s, just, **kw):
        """Chữ trên đường cơ sở: just 0 trái, 1 giữa, 2 phải."""
        a = {0: TextEntityAlignment.LEFT, 1: TextEntityAlignment.CENTER, 2: TextEntityAlignment.RIGHT}[just]
        return self._text(lay, x, y, h, s, a, **kw)

    # --- kích thước -------------------------------------------------------
    def dim(self, lay, rot, p1, p2, pd, tp=None, dimname=None):
        """Dim: điểm đo p1, p2 cố định theo hình; đường dim và chữ dịch theo item."""
        with self.item("dim", "Kích thước"):
            dxi, dyi = self.off(True)
            dxg, dyg = self.off(False)
            di = (dxi - dxg, dyi - dyg)
            if tp is None and (abs(di[0]) > 1e-9 or abs(di[1]) > 1e-9):
                g = 2.0                           # khe + nửa chiều cao chữ
                tp = ((p1[0] + p2[0]) / 2, pd[1] + g) if rot == 0.0 else (pd[0] - g, (p1[1] + p2[1]) / 2)
            a, b = self.wp(*p1, item=False), self.wp(*p2, item=False)
            base = self.wp(*pd)
            loc = self.wp(*tp) if tp else None
            # bbox: chữ quanh vị trí chữ ước lượng
            tw = 7.0
            if tp:
                self.wp(tp[0] - tw / 2, tp[1] - 1.5)
                self.wp(tp[0] + tw / 2, tp[1] + 1.5)
            elif rot == 0.0:
                self.wp((p1[0] + p2[0]) / 2 - tw / 2, pd[1])
                self.wp((p1[0] + p2[0]) / 2 + tw / 2, pd[1] + 3.2)
                self.wp(p1[0], pd[1] - 1)
                self.wp(p2[0], pd[1] + 1)
            else:
                self.wp(pd[0] - 3.2, (p1[1] + p2[1]) / 2 - tw / 2)
                self.wp(pd[0], (p1[1] + p2[1]) / 2 + tw / 2)
                self.wp(pd[0] - 1, p1[1])
                self.wp(pd[0] + 1, p2[1])
            d = self.msp.add_linear_dim(base=base, p1=a, p2=b, angle=rot, location=loc,
                                        dimstyle=dimname or self.dimname, dxfattribs={"layer": lay})
            d.render()
        lw = LAYERS.get(lay, (0, 0, 18))[2]
        blk = self.doc.blocks.get(d.dimension.dxf.geometry)
        if blk is not None:
            for e in blk:
                if e.dxftype() != "POINT":
                    e.dxf.lineweight = lw
        return d

    def dimH(self, lay, p1, p2, yd, tp=None, **kw):
        return self.dim(lay, 0.0, p1, p2, (p1[0], yd), tp, **kw)

    def dimV(self, lay, p1, p2, xd, tp=None, **kw):
        return self.dim(lay, 90.0, p1, p2, (xd, p1[1]), tp, **kw)
