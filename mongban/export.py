"""Dựng bản vẽ (DXF trong bộ nhớ) và xuất PDF / DXF."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import cad, frame, model, sheet1, sheet2
from .cad import Ctx
from .geom import Geo

SHEET_DX = 420.0
PAGE_W, PAGE_H = 420.0, 297.0


@dataclass
class Result:
    doc: object
    geo: Geo
    origins: list
    ole: list = field(default_factory=list)
    handles: list = field(default_factory=list)   # handle các đối tượng của từng tờ
    objs: list = field(default_factory=list)      # đối tượng dịch chuyển được của từng tờ


def title_values(p: dict, den: int, sheet: int, nsheet: int) -> dict:
    return {
        "TEN1": f"HÌNH THỨC MÓNG CỘT {model.HT_NAMES[int(p['HT'])]} {p['COT']}".strip(),
        "TEN2": f"MÓNG {model.type_name(p)}",
        "TL": f"1/{den}",
        "TO": f"{sheet}/{nsheet}",
        "MABV": p.get("MABV", ""),
        "GD": p.get("GD", ""),
    }


def build(p: dict, frame_path: str | None = None, fields: dict | None = None, offsets: dict | None = None) -> Result:
    err = model.validate(p)
    if err:
        raise ValueError(err)
    fields = fields or frame.DEFAULT_FIELDS
    doc, tags = frame.new_output_doc(frame_path, str(p.get("GD", "")), fields)
    g = Geo(p)
    g.calc_kl()
    detail = model.is_detail(p)
    nsheet = 2 if detail else 1
    origins = [(0.0, 0.0)]
    msp = doc.modelspace()
    handles = []
    n0 = len(msp)
    frame.place(doc, 0.0, 0.0, title_values(p, g.den, 1, nsheet), fields, tags)
    offsets = offsets or {}
    c1 = Ctx(doc, msp, 0.0, 0.0, g.den, offsets, "s1")
    sheet1.draw(c1, g)
    handles.append({e.dxf.handle for e in list(msp)[n0:]})
    objs = [c1.objs]
    if detail:
        origins.append((SHEET_DX, 0.0))
        n0 = len(msp)
        frame.place(doc, SHEET_DX, 0.0, title_values(p, g.den, 2, nsheet), fields, tags)
        c2 = Ctx(doc, msp, SHEET_DX, 0.0, g.den, offsets, "s2")
        sheet2.draw(c2, g)
        handles.append({e.dxf.handle for e in list(msp)[n0:]})
        objs.append(c2.objs)
    ole = frame.ole_images(frame_path) if frame_path else []
    return Result(doc, g, origins, ole, handles, objs)


def save_dxf(res: Result, path: str):
    res.doc.saveas(path)


def pdf_bytes(res: Result, only=None) -> bytes:
    """Mỗi tờ 1 trang A3 ngang, tỷ lệ 1:1, nét theo layer, chữ Roboto, kèm logo OLE."""
    import pymupdf
    from ezdxf.addons.drawing import Frontend, RenderContext, config, layout
    from ezdxf.addons.drawing import pymupdf as pmb
    from ezdxf.math import BoundingBox2d

    cad.init_fonts()
    cfg = config.Configuration(
        lineweight_policy=config.LineweightPolicy.ABSOLUTE,
        color_policy=config.ColorPolicy.BLACK,
        background_policy=config.BackgroundPolicy.WHITE,
        min_lineweight=0.05,
        hatch_policy=config.HatchPolicy.NORMAL,
    )
    out = pymupdf.open()
    msp = res.doc.modelspace()
    for i, (ox, oy) in enumerate(res.origins):
        if only is not None and i not in only:
            continue
        ctx = RenderContext(res.doc)
        be = pmb.PyMuPdfBackend()
        hs = res.handles[i] if i < len(res.handles) else None
        flt = (lambda e, hs=hs: e.dxf.handle in hs) if hs else None
        Frontend(ctx, be, config=cfg).draw_layout(msp, finalize=True, filter_func=flt)
        page = layout.Page(PAGE_W, PAGE_H, layout.Units.mm, margins=layout.Margins.all(0))
        data = be.get_pdf_bytes(page, settings=layout.Settings(fit_page=False, scale=1.0),
                                render_box=BoundingBox2d([(ox, oy), (ox + PAGE_W, oy + PAGE_H)]))
        src = pymupdf.open("pdf", data)
        out.insert_pdf(src)
        pg = out[-1]
        mm = 72.0 / 25.4
        for x0, y0, x1, y1, png in res.ole:
            r = pymupdf.Rect(x0 * mm, (PAGE_H - y1) * mm, x1 * mm, (PAGE_H - y0) * mm)
            pg.insert_image(r, stream=png, keep_proportion=True)
    data = out.tobytes(garbage=3, deflate=True)
    out.close()
    return data


def save_pdf(res: Result, path: str):
    with open(path, "wb") as f:
        f.write(pdf_bytes(res))
