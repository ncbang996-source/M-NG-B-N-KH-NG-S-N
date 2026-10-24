"""VẼ MÓNG BẢN - app vẽ nhanh bản vẽ móng bản (móng cột đường dây) từ file Excel, xuất PDF / DXF.

Chạy:  python app.py
"""
from __future__ import annotations

import copy
import json
import os
import sys
import threading
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

from mongban import cad, export, frame, model

APP_NAME = "Vẽ Móng Bản"
APP_VER = "1.0.0"


def settings_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~/.config")
    d = os.path.join(base, "VeMongBan")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "settings.json")


def load_settings():
    try:
        with open(settings_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(s):
    try:
        with open(settings_path(), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def default_frame():
    p = os.path.join(cad.resource_dir(), "frames", "KT-A3.dxf")
    return p if os.path.isfile(p) else ""


# (khoá, nhãn, kiểu) - kiểu: f = số, s = chữ
DIM_FIELDS = [
    ("L1", "L1 - tim chân cột theo X (m)"), ("L2", "L2 - tim chân cột theo Y (m)"),
    ("L", "L - dài móng, theo X (m)"), ("B", "B - rộng móng, theo Y (m)"), ("BB", "b - cổ móng b x b (m)"),
    ("H1", "H1 - chôn sâu (m)"), ("H2", "H2 - cao trên mặt đất (m)"),
    ("HB", "hb - cao bản giữa (m)"), ("HV", "hv - cao bản ở mép (m)"),
    ("TL", "Dày bê tông lót (m)"), ("ML", "Lót tràn ra mỗi bên (m)"), ("MPL", "Vát tràn ngoài cổ móng (m)"),
    ("HC", "Dày đệm cát (m, 0 = không có)"), ("SLOPE", "Hệ số mở mái K27 (tính KL)"),
    ("MPIT", "Mở rộng đáy hố đào (m)"),
]
REBAR_FIELDS = [
    ("Lớp dưới bản móng", "RB_BOT_D", "RB_BOT_S"), ("Lớp trên bản móng", "RB_TOP_D", "RB_TOP_S"),
    ("Thép chống", "RB_CH_D", "RB_CH_S"), ("Đai cổ móng", "RT_D", "RT_S"),
    ("Đai phụ", "RP_D", "RP_S"), ("Lưới đầu trụ", "RL_D", "RL_S"),
]
STAGES = ["TKCS", "TKBVTC", "TKKT"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} {APP_VER}")
        self.geometry("1400x860")
        self.minsize(1100, 700)
        self.st = load_settings()
        self.p = model.default_params()
        self.p.update({k: v for k, v in self.st.get("params", {}).items() if k in self.p})
        self.xls = self.st.get("xls", "")
        self.frame_path = self.st.get("frame", default_frame())
        if self.frame_path and not os.path.isfile(self.frame_path):
            self.frame_path = default_frame()
        self.fields = copy.deepcopy(self.st.get("fields") or frame.DEFAULT_FIELDS)
        self.vars: dict[str, tk.Variable] = {}
        self.pdf = None
        self.pages = []          # ảnh PIL từng trang
        self.page_i = 0
        self.zoom = None         # None = vừa khung
        self.busy = False
        self.dirty = True
        self._job = None
        self._build_ui()
        self._fill()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        if self.xls and os.path.isfile(self.xls) and not self.st.get("params"):
            self.after(200, lambda: self.read_excel(self.xls))
        else:
            self.after(300, self.preview)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista" if sys.platform == "win32" else "clam")
        except tk.TclError:
            pass
        style.configure("Head.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Err.TLabel", foreground="#b00020")
        style.configure("Ok.TLabel", foreground="#1b5e20")

        bar = ttk.Frame(self, padding=(6, 4))
        bar.pack(side="top", fill="x")
        b = lambda t, cmd: ttk.Button(bar, text=t, command=cmd)
        b("Mở Excel...", self.pick_excel).pack(side="left")
        b("Đọc lại Excel", lambda: self.read_excel(self.xls)).pack(side="left", padx=(4, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        b("Nạp khung tên...", self.pick_frame).pack(side="left")
        b("Cấu hình khung tên...", self.edit_fields).pack(side="left", padx=(4, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        b("Xem trước", self.preview).pack(side="left")
        self.v_auto = tk.BooleanVar(value=self.st.get("auto", True))
        ttk.Checkbutton(bar, text="Tự cập nhật", variable=self.v_auto).pack(side="left", padx=6)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=8)
        b("Xuất PDF...", self.export_pdf).pack(side="left")
        b("Xuất AutoCAD (DXF)...", self.export_dxf).pack(side="left", padx=(4, 0))

        info = ttk.Frame(self, padding=(8, 0))
        info.pack(side="top", fill="x")
        self.l_xls = ttk.Label(info, text="")
        self.l_xls.pack(side="left")
        self.l_frame = ttk.Label(info, text="")
        self.l_frame.pack(side="right")

        pw = ttk.PanedWindow(self, orient="horizontal")
        pw.pack(fill="both", expand=True, padx=6, pady=4)
        left = ttk.Frame(pw)
        right = ttk.Frame(pw)
        pw.add(left, weight=0)
        pw.add(right, weight=1)

        # khung trái cuộn được
        cv = tk.Canvas(left, width=430, highlightthickness=0)
        sb = ttk.Scrollbar(left, orient="vertical", command=cv.yview)
        body = ttk.Frame(cv)
        body.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.create_window((0, 0), window=body, anchor="nw")
        cv.configure(yscrollcommand=sb.set)
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._scroll_left = cv
        cv.bind("<Enter>", lambda e: cv.bind_all("<MouseWheel>", self._wheel_left))
        cv.bind("<Leave>", lambda e: cv.unbind_all("<MouseWheel>"))
        self._form(body)

        # xem trước
        top = ttk.Frame(right)
        top.pack(side="top", fill="x")
        self.v_page = tk.StringVar(value="Tờ 1")
        self.cb_page = ttk.Combobox(top, textvariable=self.v_page, state="readonly", width=8, values=["Tờ 1"])
        self.cb_page.pack(side="left")
        self.cb_page.bind("<<ComboboxSelected>>", lambda e: self._show_page(self.cb_page.current()))
        ttk.Button(top, text="Vừa khung", command=self.zoom_fit).pack(side="left", padx=4)
        ttk.Button(top, text="+", width=3, command=lambda: self.zoom_by(1.25)).pack(side="left")
        ttk.Button(top, text="−", width=3, command=lambda: self.zoom_by(0.8)).pack(side="left", padx=(2, 0))
        self.l_state = ttk.Label(top, text="")
        self.l_state.pack(side="left", padx=10)
        self.pv = tk.Canvas(right, background="#808080", highlightthickness=0)
        self.pv.pack(fill="both", expand=True)
        self.pv.bind("<Configure>", lambda e: self._redraw())
        self.pv.bind("<ButtonPress-1>", lambda e: self.pv.scan_mark(e.x, e.y))
        self.pv.bind("<B1-Motion>", lambda e: self.pv.scan_dragto(e.x, e.y, gain=1))
        self.pv.bind("<MouseWheel>", self._wheel_zoom)
        self.pv.bind("<Button-4>", lambda e: self.zoom_by(1.15))
        self.pv.bind("<Button-5>", lambda e: self.zoom_by(1 / 1.15))

        st = ttk.Frame(self, padding=(8, 2))
        st.pack(side="bottom", fill="x")
        self.l_msg = ttk.Label(st, text="")
        self.l_msg.pack(side="left")

    def _wheel_left(self, e):
        self._scroll_left.yview_scroll(int(-e.delta / 120), "units")

    def _var(self, key, kind="s"):
        v = tk.StringVar()
        v.trace_add("write", lambda *a: self._changed())
        self.vars[key] = v
        return v

    def _form(self, body):
        r = 0

        def head(t):
            nonlocal r
            ttk.Label(body, text=t, style="Head.TLabel").grid(row=r, column=0, columnspan=4, sticky="w", pady=(10, 2), padx=4)
            r += 1

        def row(lbl, key, w=12, values=None):
            nonlocal r
            ttk.Label(body, text=lbl).grid(row=r, column=0, sticky="w", padx=(10, 4), pady=1)
            if values:
                e = ttk.Combobox(body, textvariable=self._var(key), values=values, width=w - 2)
            else:
                e = ttk.Entry(body, textvariable=self._var(key), width=w)
            e.grid(row=r, column=1, columnspan=3, sticky="w", pady=1)
            r += 1
            return e

        head("1. Thông tin chung")
        row("Hình thức cột", "HT", 16, values=["Đỡ", "Néo góc", "Néo dừng"])
        row("Loại cột", "COT", 16)
        row("Tên móng (trống = tự đặt)", "TENMONG", 20)
        row("Giai đoạn thiết kế", "GD", 12, values=STAGES)
        row("Mã bản vẽ ghi chú chung", "CODE", 26)
        row("Mã số bản vẽ (khung tên)", "MABV", 26)
        row("Bê tông móng", "BTM", 8)
        row("Bê tông lót", "BTL", 8)
        row("Bu lông neo", "BLN", 16)
        head("2. Kích thước")
        for k, lbl in DIM_FIELDS:
            row(lbl, k, 8)
        head("3. Cốt thép (mm)")
        ttk.Label(body, text="Ø").grid(row=r, column=1, sticky="w")
        ttk.Label(body, text="@ (bước)").grid(row=r, column=2, sticky="w")
        r += 1
        for lbl, kd, ks in REBAR_FIELDS:
            ttk.Label(body, text=lbl).grid(row=r, column=0, sticky="w", padx=(10, 4), pady=1)
            ttk.Entry(body, textvariable=self._var(kd), width=5).grid(row=r, column=1, sticky="w")
            ttk.Entry(body, textvariable=self._var(ks), width=6).grid(row=r, column=2, sticky="w")
            r += 1
        ttk.Label(body, text="Thép chủ cổ móng: số thanh / Ø").grid(row=r, column=0, sticky="w", padx=(10, 4), pady=1)
        ttk.Entry(body, textvariable=self._var("RC_N"), width=5).grid(row=r, column=1, sticky="w")
        ttk.Entry(body, textvariable=self._var("RC_D"), width=6).grid(row=r, column=2, sticky="w")
        r += 1
        row("Số lớp lưới đầu trụ", "RL_N", 5)
        row("Lớp BT bảo vệ đáy móng (mm)", "COVER_B", 6)
        row("Lớp BT bảo vệ còn lại (mm)", "COVER", 6)
        head("4. Bản vẽ")
        ttk.Label(body, text="Tỷ lệ 1/").grid(row=r, column=0, sticky="w", padx=(10, 4))
        ttk.Combobox(body, textvariable=self._var("SCALE"), values=[str(s) for s in model.SCALES], width=6,
                     state="readonly").grid(row=r, column=1, sticky="w")
        ttk.Button(body, text="Tự chọn", command=self.auto_scale).grid(row=r, column=2, sticky="w")
        r += 1
        self.l_info = ttk.Label(body, text="", wraplength=410, justify="left")
        self.l_info.grid(row=r, column=0, columnspan=4, sticky="w", padx=6, pady=(10, 2))
        r += 1
        self.l_err = ttk.Label(body, text="", style="Err.TLabel", wraplength=410, justify="left")
        self.l_err.grid(row=r, column=0, columnspan=4, sticky="w", padx=6)

    # ------------------------------------------------------------ dữ liệu
    def _fill(self):
        self._filling = True
        p = self.p
        for k, v in self.vars.items():
            if k == "HT":
                v.set(["Đỡ", "Néo góc", "Néo dừng"][int(p["HT"])])
            elif k in ("COVER", "COVER_B"):
                v.set(f"{p[k] * 1000:g}")
            elif k in ("SCALE",):
                v.set(str(int(p[k])))
            elif isinstance(p.get(k), float):
                v.set(f"{p[k]:g}")
            else:
                v.set(str(p.get(k, "")))
        self._filling = False
        self.l_xls.config(text=f"Excel: {self.xls or '(chưa chọn)'}")
        self.l_frame.config(text=f"Khung tên: {os.path.basename(self.frame_path) if self.frame_path else '(khung A3 đơn giản)'}")
        self._update_info()

    def _collect(self):
        p = dict(self.p)
        for k, v in self.vars.items():
            s = v.get().strip()
            if k == "HT":
                p["HT"] = {"đỡ": 0, "néo góc": 1, "néo dừng": 2}.get(s.lower(), model.ht_from_string(s))
            elif k in ("COVER", "COVER_B"):
                p[k] = float(s.replace(",", ".")) / 1000.0
            elif k == "SCALE":
                p[k] = int(float(s))
            elif isinstance(model.default_params().get(k), float):
                p[k] = float(s.replace(",", "."))
            else:
                p[k] = s
        return p

    def _changed(self):
        if getattr(self, "_filling", False):
            return
        self.dirty = True
        self._update_info()
        if self.v_auto.get():
            if self._job:
                self.after_cancel(self._job)
            self._job = self.after(1200, self.preview)

    def _update_info(self):
        try:
            p = self._collect()
        except ValueError:
            self.l_err.config(text="[!] Có ô nhập không phải số.")
            return None
        err = model.validate(p)
        self.l_err.config(text=f"[!] {err}" if err else "")
        if not err:
            txt = (f"Loại móng: {model.type_name(p)}    H = H1 + H2 = {model.H(p):.2f} m\n"
                   f"BT móng = {model.vol_mong(p):.2f} m³ ({p['BTM']})   BT lót = {model.vol_lot(p):.2f} m³ ({p['BTL']})")
            if p["HC"] > 0:
                txt += f"\nĐệm cát = {model.vol_cat(p):.2f} m³   Vải địa = {model.area_vai(p):.2f} m²"
            txt += f"\nSố tờ: {'2 (có tờ chi tiết thép)' if model.is_detail(p) else '1'}"
            self.l_info.config(text=txt)
        return None if err else p

    def auto_scale(self):
        try:
            p = self._collect()
            self.vars["SCALE"].set(str(model.auto_scale(p)))
        except ValueError:
            pass

    # ---------------------------------------------------------- hành động
    def pick_excel(self):
        f = filedialog.askopenfilename(title="Chọn file Excel (sheet TONG HOP)",
                                       filetypes=[("Excel", "*.xlsx *.xlsm"), ("Tất cả", "*.*")],
                                       initialdir=os.path.dirname(self.xls) if self.xls else None)
        if f:
            self.read_excel(f)

    def read_excel(self, path):
        if not path:
            return self.pick_excel()
        try:
            p, warn = model.read_excel(path, "TONG HOP", self.p)
        except Exception as ex:
            messagebox.showerror(APP_NAME, f"Không đọc được file Excel:\n{ex}")
            return
        if model.validate(p) is None and int(p["SCALE"]) < model.auto_scale(p):
            p["SCALE"] = model.auto_scale(p)          # tỷ lệ hiện tại không đủ chỗ -> tự chọn
        self.p, self.xls = p, path
        self._fill()
        msg = f"Đã đọc {os.path.basename(path)}."
        if warn:
            msg += "  Cảnh báo: " + " ".join(warn)
        self.l_msg.config(text=msg)
        self.preview()

    def pick_frame(self):
        f = filedialog.askopenfilename(title="Chọn file DXF khung tên", filetypes=[("DXF", "*.dxf")])
        if not f:
            return
        try:
            doc, tags = frame.new_output_doc(f, "TKBVTC", self.fields)
        except Exception as ex:
            messagebox.showerror(APP_NAME, f"Không nạp được khung tên:\n{ex}")
            return
        self.frame_path = f
        self._fill()
        msg = f"Đã nạp khung tên {os.path.basename(f)}."
        if tags:
            msg += " Attribute: " + ", ".join(sorted(tags))
        self.l_msg.config(text=msg)
        self.preview()

    def edit_fields(self):
        FieldsDialog(self)

    def _render(self, p, done):
        def work():
            try:
                res = export.build(p, self.frame_path or None, self.fields)
                data = export.pdf_bytes(res)
                imgs = pdf_images(data)
                self.after(0, lambda: done(res, data, imgs, None))
            except Exception as ex:
                tb = traceback.format_exc()
                self.after(0, lambda: done(None, None, None, (ex, tb)))
        threading.Thread(target=work, daemon=True).start()

    def preview(self):
        self._job = None
        if self.busy:
            self._job = self.after(800, self.preview)
            return
        p = self._update_info()
        if p is None:
            return
        self.busy = True
        self.l_state.config(text="Đang dựng bản vẽ...")
        self.config(cursor="watch")

        def done(res, data, imgs, err):
            self.busy = False
            self.config(cursor="")
            if err:
                self.l_state.config(text="Lỗi khi dựng bản vẽ")
                messagebox.showerror(APP_NAME, f"{err[0]}\n\n{err[1][-1500:]}")
                return
            self.res, self.pdf, self.pages = res, data, imgs
            self.dirty = False
            vals = [f"Tờ {i + 1}" for i in range(len(imgs))]
            self.cb_page.config(values=vals)
            self._show_page(min(self.page_i, len(imgs) - 1))
            self.l_state.config(text=f"{len(imgs)} tờ A3 - tỷ lệ 1/{res.geo.den}")
        self._render(p, done)

    def _ensure_fresh(self, then):
        if self.pdf is not None and not self.dirty:
            return then()
        p = self._update_info()
        if p is None:
            messagebox.showwarning(APP_NAME, self.l_err.cget("text") or "Số liệu chưa hợp lệ.")
            return
        self.busy = True
        self.l_state.config(text="Đang dựng bản vẽ...")

        def done(res, data, imgs, err):
            self.busy = False
            if err:
                messagebox.showerror(APP_NAME, f"{err[0]}")
                return
            self.res, self.pdf, self.pages, self.dirty = res, data, imgs, False
            self.cb_page.config(values=[f"Tờ {i + 1}" for i in range(len(imgs))])
            self._show_page(min(self.page_i, len(imgs) - 1))
            then()
        self._render(p, done)

    def _default_name(self, ext):
        p = self.p
        nm = f"MONG_{model.type_name(p)}_{p.get('COT', '')}_{p.get('GD', '')}".replace(" ", "_").replace("/", "-")
        return nm + ext

    def export_pdf(self):
        def go():
            f = filedialog.asksaveasfilename(title="Xuất PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                             initialfile=self._default_name(".pdf"),
                                             initialdir=os.path.dirname(self.xls) if self.xls else None)
            if f:
                try:
                    with open(f, "wb") as fh:
                        fh.write(self.pdf)
                    self.l_msg.config(text=f"Đã xuất PDF: {f}")
                except OSError as ex:
                    messagebox.showerror(APP_NAME, f"Không ghi được file:\n{ex}")
        self._ensure_fresh(go)

    def export_dxf(self):
        def go():
            f = filedialog.asksaveasfilename(title="Xuất AutoCAD (DXF)", defaultextension=".dxf",
                                             filetypes=[("AutoCAD DXF", "*.dxf")],
                                             initialfile=self._default_name(".dxf"),
                                             initialdir=os.path.dirname(self.xls) if self.xls else None)
            if f:
                try:
                    export.save_dxf(self.res, f)
                    self.l_msg.config(text=f"Đã xuất DXF: {f}  (mở bằng AutoCAD, Save As .dwg nếu cần)")
                except Exception as ex:
                    messagebox.showerror(APP_NAME, f"Không ghi được file:\n{ex}")
        self._ensure_fresh(go)

    # ------------------------------------------------------------ xem trước
    def _show_page(self, i):
        if not self.pages:
            return
        self.page_i = max(0, i)
        self.v_page.set(f"Tờ {self.page_i + 1}")
        self._redraw()

    def zoom_fit(self):
        self.zoom = None
        self._redraw()

    def zoom_by(self, f):
        if not self.pages:
            return
        self.zoom = min(4.0, max(0.1, (self.zoom or self._fit_zoom()) * f))
        self._redraw()

    def _wheel_zoom(self, e):
        self.zoom_by(1.15 if e.delta > 0 else 1 / 1.15)

    def _fit_zoom(self):
        im = self.pages[self.page_i]
        w, h = max(50, self.pv.winfo_width() - 20), max(50, self.pv.winfo_height() - 20)
        return min(w / im.width, h / im.height)

    def _redraw(self):
        from PIL import ImageTk
        if not self.pages:
            return
        im = self.pages[self.page_i]
        z = self.zoom or self._fit_zoom()
        w, h = max(1, int(im.width * z)), max(1, int(im.height * z))
        self._tkimg = ImageTk.PhotoImage(im.resize((w, h), resample=3))
        self.pv.delete("all")
        cw, ch = self.pv.winfo_width(), self.pv.winfo_height()
        x0 = max(10, (cw - w) // 2)
        y0 = max(10, (ch - h) // 2)
        self.pv.create_rectangle(x0 + 4, y0 + 4, x0 + w + 4, y0 + h + 4, fill="#555", outline="")
        self.pv.create_image(x0, y0, image=self._tkimg, anchor="nw")
        self.pv.configure(scrollregion=(0, 0, max(cw, w + 20), max(ch, h + 20)))

    def on_close(self):
        try:
            p = self._collect()
        except ValueError:
            p = self.p
        save_settings({"xls": self.xls, "frame": self.frame_path, "fields": self.fields,
                       "auto": self.v_auto.get(), "params": p})
        self.destroy()


def pdf_images(data, dpi=150):
    import pymupdf
    from PIL import Image
    out = []
    with pymupdf.open("pdf", data) as d:
        for pg in d:
            pix = pg.get_pixmap(dpi=dpi)
            out.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    return out


class FieldsDialog(tk.Toplevel):
    """Chỉnh vị trí các ô điền trong khung tên (toạ độ mm trong khung)."""

    COLS = [("x", 8), ("y", 8), ("h", 6), ("align", 6), ("wmax", 7)]

    def __init__(self, app: App):
        super().__init__(app)
        self.app = app
        self.title("Cấu hình khung tên")
        self.transient(app)
        self.resizable(False, False)
        f = ttk.Frame(self, padding=10)
        f.pack(fill="both")
        ttk.Label(f, text="Toạ độ (mm) tính từ góc dưới trái khung. align: L trái, C giữa (đường cơ sở), "
                          "MC giữa, R phải.\nNếu khung có attribute (TENBV, TYLE, TO, MASO...), app điền vào "
                          "attribute và bỏ qua ô tương ứng.", wraplength=560, justify="left").grid(
            row=0, column=0, columnspan=8, sticky="w", pady=(0, 8))
        ttk.Label(f, text="Ô thông tin").grid(row=1, column=0, sticky="w")
        for j, (c, _) in enumerate(self.COLS):
            ttk.Label(f, text=c).grid(row=1, column=j + 1)
        ttk.Label(f, text="đậm").grid(row=1, column=len(self.COLS) + 1)
        self.v = {}
        for i, (k, lbl) in enumerate(frame.FIELD_LABELS.items()):
            cfg = app.fields.get(k, frame.DEFAULT_FIELDS[k])
            ttk.Label(f, text=lbl).grid(row=i + 2, column=0, sticky="w", padx=(0, 8))
            for j, (c, w) in enumerate(self.COLS):
                var = tk.StringVar(value=str(cfg.get(c, "")))
                ttk.Entry(f, textvariable=var, width=w).grid(row=i + 2, column=j + 1, padx=2, pady=1)
                self.v[(k, c)] = var
            bv = tk.BooleanVar(value=bool(cfg.get("bold")))
            ttk.Checkbutton(f, variable=bv).grid(row=i + 2, column=len(self.COLS) + 1)
            self.v[(k, "bold")] = bv
        bf = ttk.Frame(f)
        bf.grid(row=20, column=0, columnspan=8, sticky="e", pady=(10, 0))
        ttk.Button(bf, text="Mặc định", command=self.reset).pack(side="left")
        ttk.Button(bf, text="Lưu", command=self.ok).pack(side="left", padx=6)
        ttk.Button(bf, text="Huỷ", command=self.destroy).pack(side="left")

    def reset(self):
        for (k, c), var in self.v.items():
            var.set(frame.DEFAULT_FIELDS[k].get(c, "") if c != "bold" else bool(frame.DEFAULT_FIELDS[k].get("bold")))

    def ok(self):
        out = copy.deepcopy(self.app.fields)
        try:
            for (k, c), var in self.v.items():
                cfg = out.setdefault(k, copy.deepcopy(frame.DEFAULT_FIELDS[k]))
                if c == "bold":
                    cfg[c] = bool(var.get())
                elif c == "align":
                    cfg[c] = var.get().strip().upper() or "L"
                else:
                    cfg[c] = float(var.get().replace(",", "."))
        except ValueError:
            messagebox.showerror(APP_NAME, "Toạ độ / chiều cao phải là số.", parent=self)
            return
        self.app.fields = out
        self.destroy()
        self.app.dirty = True
        self.app.preview()


def main():
    cad.init_fonts()
    App().mainloop()


if __name__ == "__main__":
    main()
