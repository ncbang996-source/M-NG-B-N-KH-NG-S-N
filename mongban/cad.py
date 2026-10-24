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
    "DAI":       (2, "CONTINUOUS", 40),  # thép đai, thép phân bố, lưới
    "COTTHEP":   (1, "CONTINUOUS", 50),  # thép chủ
}
STYLE = "ROBOTO"
STYLE_B = "ROBOTO-B"


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
def _font(name="Roboto-Regular.ttf"):
    init_fonts()
    from ezdxf.fonts import fonts
    return fonts.make_font(name, 1.0)


def txtw(s: str, h: float, bold=False) -> float:
    """Bề rộng thật của dòng chữ (chiều cao chữ h)."""
    s = s.replace("%%C", "Ø").replace("%%c", "Ø").replace("%%P", "±").replace("%%p", "±")
    try:
        return _font("Roboto-Bold.ttf" if bold else "Roboto-Regular.ttf").text_width(s) * h
    except Exception:
        return 0.62 * h * len(s)


def new_doc():
    init_fonts()
    doc = ezdxf.new("R2018", setup=True, units=4)
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LTSCALE"] = 1.0
    doc.header["$PSLTSCALE"] = 0
    doc.header["$LWDISPLAY"] = 1
    if STYLE not in doc.styles:
        doc.styles.new(STYLE, dxfattribs={"font": "Roboto-Regular.ttf"})
    if STYLE_B not in doc.styles:
        doc.styles.new(STYLE_B, dxfattribs={"font": "Roboto-Bold.ttf"})
    for name, (col, lt, lw) in LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, color=col, linetype=lt if lt in doc.linetypes else "CONTINUOUS", lineweight=lw)
    return doc


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


class Ctx:
    """Vẽ vào modelspace với gốc toạ độ o (góc dưới trái khung tên)."""

    def __init__(self, doc, msp, ox=0.0, oy=0.0, den=100):
        self.doc, self.msp, self.ox, self.oy = doc, msp, ox, oy
        self.set_scale(den)

    def set_scale(self, den):
        self.den = int(den)
        self.dimname = ensure_dimstyle(self.doc, self.den)

    def wp(self, x, y):
        return (self.ox + x, self.oy + y)

    # --- hình học ---------------------------------------------------------
    def ln(self, lay, x1, y1, x2, y2):
        return self.msp.add_line(self.wp(x1, y1), self.wp(x2, y2), dxfattribs={"layer": lay})

    def pl(self, lay, closed, pts, width=0.0, bulges=None):
        pp = []
        for i, p in enumerate(pts):
            b = bulges[i] if bulges else 0.0
            x, y = self.wp(p[0], p[1])
            pp.append((x, y, width, width, b))
        return self.msp.add_lwpolyline(pp, format="xyseb", close=closed, dxfattribs={"layer": lay})

    def rect(self, lay, x1, y1, x2, y2):
        return self.pl(lay, True, [(x1, y1), (x2, y1), (x2, y2), (x1, y2)])

    def ci(self, lay, x, y, r):
        return self.msp.add_circle(self.wp(x, y), r, dxfattribs={"layer": lay})

    def disc(self, lay, x, y, r):
        """Chấm tròn đặc bán kính r (polyline bề rộng r)."""
        return self.pl(lay, True, [(x - r / 2, y), (x + r / 2, y)], width=r, bulges=[1.0, 1.0])

    def arrow(self, lay, x1, y1, x2, y2, ln, wid):
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy)
        if d < 1e-9:
            return
        ux, uy = dx / d, dy / d
        bx, by = x2 - ux * ln, y2 - uy * ln
        self.msp.add_solid([self.wp(bx - uy * wid, by + ux * wid), self.wp(bx + uy * wid, by - ux * wid),
                            self.wp(x2, y2), self.wp(x2, y2)], dxfattribs={"layer": lay})

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
        t = self.msp.add_text(s, height=h, rotation=rot,
                              dxfattribs={"layer": lay, "style": STYLE_B if bold else STYLE})
        t.set_placement(self.wp(x, y), align=align)
        if underline:
            self._underline(lay, x, y, h, s, align, bold)
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

    def mtx(self, lay, x, y, h, w, s):
        m = self.msp.add_mtext(s, dxfattribs={"layer": lay, "style": STYLE, "char_height": h, "width": w,
                                                "attachment_point": 1})
        m.set_location(self.wp(x, y))
        return m

    # --- kích thước -------------------------------------------------------
    def dim(self, lay, rot, p1, p2, pd, tp=None, dimname=None):
        loc = self.wp(*tp) if tp else None
        d = self.msp.add_linear_dim(base=self.wp(*pd), p1=self.wp(*p1), p2=self.wp(*p2), angle=rot,
                                    location=loc, dimstyle=dimname or self.dimname,
                                    dxfattribs={"layer": lay})
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
