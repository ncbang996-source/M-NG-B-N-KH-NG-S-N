# VE_MONGBANKOSUON

App Windows chạy offline để vẽ nhanh bản vẽ **móng bản (móng cột đường dây)** từ file Excel. Cách làm giống lệnh Lisp `VEMONG` trong `MONG_BAN_KHONG_SUON.lsp`.

## Chức năng
- **Đọc Excel:** lấy số liệu từ sheet `TONG HOP` (kích thước, đệm cát, cốt thép, lớp bảo vệ, hình thức cột, giai đoạn...).
- **Hiệu chỉnh:** sửa mọi thông số trên giao diện; app kiểm tra số liệu và tính ngay khối lượng bê tông, đệm cát, vải địa.
- **Khung tên:** nạp file `.dxf`, mặc định dùng `assets/frames/KT-A3.dxf`.
  - Chữ "TKCS"/"TKBVTC" trong khung tự đổi theo giai đoạn.
  - Tên bản vẽ, tỷ lệ, tờ và mã số được điền theo toạ độ; chỉnh toạ độ ở **Cấu hình khung tên**.
  - Nếu khung có attribute (TENBV, TYLE, TO, MASO...), app điền vào attribute.
  - Logo đặt dạng OLE trong khung được trích ra và chèn vào PDF.
- **Xem trước:** hiển thị đúng bản sẽ in PDF.
  - TKCS có 1 tờ: hình thức móng.
  - TKBVTC có 2 tờ: thêm tờ chi tiết thép.
- **Xuất PDF:** A3, tỷ lệ 1:1, nét theo layer, font Roboto.
- **Xuất AutoCAD (.dxf):** giữ layer có độ dày nét, dimension thật và khung tên dạng block. Mở bằng AutoCAD rồi Save As `.dwg` nếu cần.
- **Xuất Excel khối lượng:** sheet THONG SO (số liệu đầu vào) và KHOI LUONG (công thức): bê tông, lót, đệm cát, vải địa, đào đất, đắp đất, đất thừa, ván khuôn, cốt thép.
- **Sắp xếp (kéo thả):** kéo từng chữ, dim, chú thích, bảng hoặc cả hình để tránh chồng nhau; bản vẽ cập nhật ngay khi thả chuột.
  - Kéo tag thép: leader tự co giãn, điểm bắt vào thép giữ nguyên. Muốn đổi thanh thép được chỉ vào thì kéo vòng tròn xanh lá ở đầu leader.
  - Chuột phải để trả về mặc định. Vị trí lưu vào `<tên Excel>.layout.json`.
- Tên file xuất mặc định trùng tên file Excel đầu vào.

## Độ dày nét (theo layer)
| Layer | Nét | Đối tượng |
|---|---|---|
| TRUC, HATCH | 0,13 | trục, hatch |
| DIM, CHU, HINH THUC, BANG | 0,18 | kích thước, chữ, leader, đường bao thường, bảng |
| MAIN, MAT CAT, VAI DIA | 0,30 | đường bao móng, ký hiệu mặt cắt, vải địa |
| DAI | 0,40 | thép đai, thép phân bố, lưới |
| COTTHEP | 0,50 | thép chủ |

## Tải file .exe
Vào tab **Actions** của repo, mở lần build mới nhất, tải mục **VE_MONGBANKOSUON-exe** ở phần *Artifacts*.

## Tự build trên máy Windows
Cài Python 3.12, rồi bấm đúp `build.bat`. File tạo ra là `dist\VE_MONGBANKOSUON.exe`.

## Chạy từ mã nguồn
```
pip install -r requirements.txt
python app.py
```
