# Prompt mở đầu cho app VẼ MÓNG BẢN CÓ SƯỜN

Dán toàn bộ phần dưới đường kẻ vào cuộc trò chuyện Claude Code mới, kèm file Excel mẫu, Lisp và bản vẽ mẫu của móng có sườn.

---

Tôi đã có app **VE_MONGBANKOSUON** (vẽ móng bản không sườn) trong repo
`ncbang996-source/M-NG-B-N-KH-NG-S-N`, nhánh `claude/ve-mong-ban`. Hãy gắn repo đó (add_repo) để đọc code tham khảo.

Bây giờ tôi muốn làm app mới **VE_MONGBANCOSUON** cho **móng bản có sườn**, làm việc tương tự app cũ. Hãy tạo app trong repo mới (tôi sẽ tạo và đưa link). Trong repo đó, tái sử dụng tối đa kiến trúc và code của app cũ, chỉ viết lại phần hình học và bản vẽ riêng của móng có sườn.

## Những phần giữ nguyên từ app cũ
- **Kiến trúc** (thư mục `mongban/`):
  - `model.py`: đọc Excel, tham số mặc định, kiểm tra hợp lệ.
  - `geom.py`: bố trí hình học, thép, bảng thống kê thép.
  - `cad.py`: Ctx, Obj, item, group, table; layer, nét, font, dim, hatch.
  - `sheet1.py` (tờ 1/2: mặt cắt, mặt bằng hố đào, tổng hợp khối lượng) và `sheet2.py` (tờ 2/2: bố trí thép, thống kê thép).
  - `frame.py`: khung tên DXF dạng block KHUNG_TEN, điền attribute hoặc theo toạ độ, logo OLE.
  - `export.py`: một doc ezdxf dùng chung cho DXF và PDF.
  - `kl_excel.py`: Excel khối lượng có công thức.
  - `_meta.py` và `app.py`: giao diện Tkinter.
- **Nét in:** trục 0.13; dim, chữ, leader, bảng 0.18; bao móng, mặt cắt, vải địa 0.30; đai 0.35; thép chủ 0.50.
- **Chữ:** font Roboto Condensed (file `Roboto_Condensed-Regular.ttf`), Height 0, Width Factor 0.8, chữ không chồng nhau.
- **Mái hố đào và khối lượng:** mái vẽ 1:0.5; khối lượng đào và đắp tính theo hệ số mái trong Excel. Khối lượng thép luôn tính theo hình học.
- **Sắp xếp bằng kéo thả:** kéo dịch đối tượng hoặc nhóm, lưu vào `<excel>.layout.json`, áp dụng cho cả PDF và DXF, cập nhật ngay khi thả chuột. Leader tự co giãn; điểm neo vào thép cố định, nhưng vẫn kéo riêng được.
- **File xuất:** tên trùng tên Excel; Excel khối lượng thêm đuôi `_KL.xlsx`.
- **Excel khối lượng:** gồm các sheet TONG KE, THONG SO, KHOI LUONG.
  - Đền bù: rộng = B + 1, dài = L + 1, diện = rộng × dài.
  - Mỗi số liệu nằm ở một ô.
- **Thép bản móng:** thép theo phương cạnh dài nằm lớp ngoài cùng; thanh chống buộc theo phương cạnh ngắn.
- **Giao diện:** có màu sắc, icon 3D 48 px, dòng "Tác giả: Nguyễn Công Bằng" ở góc dưới trái (mã hoá, khó xoá).
- **Build:** bằng GitHub Actions (windows-latest, PyInstaller, chạy smoke test trước), exe tải ở mục Artifacts. Khung tên mặc định là KT-A3.dxf.

## Phần mới cần làm cho móng có sườn
1. Đọc Excel và Lisp tôi gửi, liệt kê các ô thông số. Ví dụ: kích thước sườn (rộng, cao), số sườn và phương sườn, thép sườn (trên, dưới, giá), đai sườn, bản cánh.
2. Vẽ mặt cắt qua sườn và mặt bằng bố trí sườn.
3. Vẽ chi tiết thép sườn: thép dọc, đai, thép giá, đoạn neo vào cổ móng.
4. Vẽ chi tiết giao giữa sườn với cổ móng và với bản móng.
5. Cập nhật bảng thống kê thép và khối lượng bê tông, ván khuôn, đào, đắp có tính sườn.
6. Hỏi lại tôi từng điểm chưa rõ trước khi code. Gửi ảnh xem trước bản vẽ trước khi xuất file.

Tôi gửi kèm: Excel mẫu (sheet TONG HOP), file Lisp, bản vẽ mẫu PDF hoặc DWG của móng có sườn, và khung tên KT-A3.dxf.
