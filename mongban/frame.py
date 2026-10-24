"""Khung tên: nạp file DXF, chuyển thành block, điền thông tin (attribute hoặc toạ độ cố định), trích logo OLE."""
from __future__ import annotations

import io
import os
import struct

import ezdxf

from . import cad

BLOCK = "KHUNG_TEN"
STAGE_WORDS = {"TKCS", "TKBVTC", "TKKT", "BVTC", "TKTC"}

# Vị trí các ô điền thông tin (toạ độ trong khung, mm) - mặc định theo khung KT-A3 (SEIAC)
DEFAULT_FIELDS = {
    "TEN1": {"x": 372.2, "y": 27.3, "h": 2.0, "align": "MC", "wmax": 72.0, "bold": False,
             "box": [334.7, 20.0, 409.6, 31.0]},
    "TEN2": {"x": 372.2, "y": 22.6, "h": 2.5, "align": "MC", "wmax": 72.0, "bold": False, "box": None},
    "TL":   {"x": 340.4, "y": 11.0, "h": 2.0, "align": "L", "wmax": 9.0, "bold": False, "box": None},
    "TO":   {"x": 357.4, "y": 11.0, "h": 2.0, "align": "L", "wmax": 7.0, "bold": False, "box": None},
    "MABV": {"x": 387.2, "y": 15.0, "h": 2.5, "align": "MC", "wmax": 43.0, "bold": True,
             "box": [364.7, 10.0, 409.6, 20.0]},
}
FIELD_LABELS = {"TEN1": "Tên bản vẽ (dòng 1)", "TEN2": "Tên bản vẽ (dòng 2)", "TL": "Tỷ lệ",
                "TO": "Tờ", "MABV": "Mã số bản vẽ"}
# tag attribute được nhận theo các tên thường gặp
TAG_SYNONYMS = {
    "TEN1": {"TEN1", "TENBV", "TENBV1", "TEN_BV", "TEN_BAN_VE", "TITLE", "TITLE1"},
    "TEN2": {"TEN2", "TENBV2", "TITLE2"},
    "TL": {"TL", "TYLE", "TY_LE", "SCALE"},
    "TO": {"TO", "SOTO", "SO_TO", "SHEET", "TO_SO"},
    "MABV": {"MABV", "MASO", "MA_SO", "MA_BV", "DWGNO", "DRAWING_NO", "SOBV"},
    "GD": {"GD", "GIAIDOAN", "GIAI_DOAN", "STAGE"},
}


_ole_cache: dict = {}


def ole_images(path: str):
    """Trả về danh sách (x0, y0, x1, y1, png_bytes) cho các OLE2FRAME chứa ảnh bitmap."""
    try:
        key = (os.path.abspath(path), os.path.getmtime(path))
    except OSError:
        return []
    if key not in _ole_cache:
        _ole_cache[key] = _ole_images(path)
    return _ole_cache[key]


def _ole_images(path: str):
    out = []
    try:
        doc = ezdxf.readfile(path)
    except Exception:
        return out
    for e in doc.modelspace().query("OLE2FRAME"):
        try:
            tags = e.acdb_ole2frame
            p1 = p2 = None
            chunks = []
            for t in tags:
                if t.code == 10:
                    p1 = t.value
                elif t.code == 11:
                    p2 = t.value
                elif t.code == 310:
                    chunks.append(t.value)
            png = _dib_to_png(b"".join(chunks))
            if png and p1 and p2:
                out.append((min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1]), png))
        except Exception:
            continue
    return out


def _dib_to_png(data: bytes):
    from PIL import Image
    i = 0
    while True:
        i = data.find(b"\x28\x00\x00\x00", i)
        if i < 0:
            return None
        w, h, planes, bpp = struct.unpack("<iiHH", data[i + 4:i + 16])
        if planes == 1 and bpp in (1, 4, 8, 24, 32) and 0 < w < 20000 and 0 < abs(h) < 20000:
            comp = struct.unpack("<I", data[i + 16:i + 20])[0]
            ncol = struct.unpack("<I", data[i + 32:i + 36])[0] or ((1 << bpp) if bpp <= 8 else 0)
            if comp == 3:
                ncol = 3
            rowsz = ((w * bpp + 31) // 32) * 4
            size = 40 + ncol * 4 + rowsz * abs(h)
            if i + size <= len(data):
                bmp = b"BM" + struct.pack("<IHHI", 14 + size, 0, 0, 14 + 40 + ncol * 4) + data[i:i + size]
                try:
                    im = Image.open(io.BytesIO(bmp)).convert("RGB")
                    buf = io.BytesIO()
                    im.save(buf, "PNG")
                    return buf.getvalue()
                except Exception:
                    pass
        i += 1


def _fix_fonts(doc):
    """Kiểu chữ dùng font không có trên máy -> Roboto tương ứng."""
    from ezdxf.fonts import fonts
    cad.init_fonts()
    for st in doc.styles:
        f = (st.dxf.get("font") or "").strip()
        if not f:
            continue
        try:
            ok = fonts.font_manager.has_font(f)
        except Exception:
            ok = False
        if not ok:
            st.dxf.font = "RobotoCondensed-Regular.ttf" if "cond" in f.lower() else "Roboto-Regular.ttf"


def setup_doc(doc):
    """Thêm layer, kiểu chữ, linetype trục vào 1 document có sẵn."""
    cad.init_fonts()
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    doc.header["$LWDISPLAY"] = 1
    if "MB_CENTER" not in doc.linetypes:
        doc.linetypes.add("MB_CENTER", pattern=[5.9, 4.0, -0.8, 0.3, -0.8], description="Truc ____ . ____ .")
    if cad.STYLE not in doc.styles:
        doc.styles.new(cad.STYLE, dxfattribs={"font": "Roboto-Regular.ttf"})
    if cad.STYLE_B not in doc.styles:
        doc.styles.new(cad.STYLE_B, dxfattribs={"font": "Roboto-Bold.ttf"})
    for name, (col, lt, lw) in cad.LAYERS.items():
        ltn = "MB_CENTER" if lt == "CENTER" else "CONTINUOUS"
        if name in doc.layers:
            la = doc.layers.get(name)
            la.dxf.color, la.dxf.linetype, la.dxf.lineweight = col, ltn, lw
        else:
            doc.layers.add(name, color=col, linetype=ltn, lineweight=lw)
    if "KHUNG" not in doc.layers:
        doc.layers.add("KHUNG", color=7, lineweight=35)
    _fix_fonts(doc)


def new_output_doc(frame_path: str | None, stage: str, fields: dict | None = None):
    """Tạo document xuất: nếu có khung tên thì dùng chính file khung (giữ OLE, block chữ ký...)."""
    has_frame = bool(frame_path and os.path.isfile(frame_path))
    if has_frame:
        doc = ezdxf.readfile(frame_path)
        setup_doc(doc)
        msp = doc.modelspace()
        blk = doc.blocks.new(BLOCK) if BLOCK not in doc.blocks else doc.blocks.get(BLOCK)
        for e in list(msp):
            msp.move_to_layout(e, blk)
        boxes = [f["box"] for f in (fields or DEFAULT_FIELDS).values() if f.get("box")]
        for e in list(blk):
            if e.dxftype() in ("TEXT", "MTEXT"):
                pt = e.dxf.insert
                if e.dxftype() == "TEXT" and e.dxf.halign + e.dxf.valign and e.dxf.hasattr("align_point"):
                    pt = e.dxf.align_point
                if any(b[0] <= pt.x <= b[2] and b[1] <= pt.y <= b[3] for b in boxes):
                    blk.delete_entity(e)      # chữ cũ trong ô sẽ điền lại
        tags = set()
        for e in blk:
            if e.dxftype() == "TEXT" and e.dxf.text.strip().upper() in STAGE_WORDS:
                e.dxf.text = stage
            elif e.dxftype() == "ATTDEF":
                tags.add(e.dxf.tag.upper())
        return doc, tags
    doc = ezdxf.new("R2018", setup=True, units=4)
    setup_doc(doc)
    blk = doc.blocks.new(BLOCK)
    _simple_frame(blk)
    return doc, set()


def _simple_frame(blk):
    """Khung A3 đơn giản khi chưa nạp khung tên."""
    a = {"layer": "KHUNG"}
    blk.add_lwpolyline([(20, 10), (409.6, 10), (409.6, 286.7), (20, 286.7)], close=True, dxfattribs=a)
    blk.add_lwpolyline([(264.8, 10), (409.6, 10), (409.6, 50), (264.8, 50)], close=True, dxfattribs=a)
    for y in (20, 35):
        blk.add_line((264.8, y), (409.6, y), dxfattribs=a)
    for x in (334.7, 364.7):
        blk.add_line((x, 10), (x, 35 if x == 334.7 else 20), dxfattribs=a)
    blk.add_line((349.7, 10), (349.7, 20), dxfattribs=a)
    blk.add_line((334.7, 15), (364.7, 15), dxfattribs=a)
    for s_, x, y in (("TÊN BẢN VẼ:", 336.0, 31.4), ("TL:", 336.0, 11.0), ("TỜ:", 351.0, 11.0)):
        t = blk.add_text(s_, height=2.0, dxfattribs={"layer": "KHUNG", "style": cad.STYLE})
        t.set_placement((x, y))


def match_tag(tags, field):
    for t in tags:
        if t in TAG_SYNONYMS.get(field, {field}):
            return t
    return None


def place(doc, ox, oy, values: dict, fields: dict, tags: set):
    """Chèn khung tên tại (ox, oy) và điền thông tin."""
    msp = doc.modelspace()
    ins = msp.add_blockref(BLOCK, (ox, oy), dxfattribs={"layer": "0"})
    if tags:
        av = {}
        for f, v in values.items():
            t = match_tag(tags, f)
            if t:
                av[t] = v
        ins.add_auto_attribs(av)
    done = {f for f in values if tags and match_tag(tags, f)}
    for f, v in values.items():
        if f in done or f not in fields or not v:
            continue
        cfg = fields[f]
        h = float(cfg.get("h", 2.0))
        bold = bool(cfg.get("bold"))
        w = cad.txtw(v, h, bold)
        wmax = float(cfg.get("wmax", 0) or 0)
        if wmax and w > wmax:
            h *= wmax / w
        from ezdxf.enums import TextEntityAlignment as A
        al = {"MC": A.MIDDLE_CENTER, "L": A.LEFT, "C": A.CENTER, "R": A.RIGHT}.get(cfg.get("align", "L"), A.LEFT)
        t = msp.add_text(v, height=h, dxfattribs={"layer": "CHU", "style": cad.STYLE_B if bold else cad.STYLE})
        t.set_placement((ox + float(cfg["x"]), oy + float(cfg["y"])), align=al)
    return ins
