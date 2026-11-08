# Rà soát lỗ hổng mã nguồn Agent (tuần 3)

Rà soát 3 file: agent/core.py, agent/tools.py, lab/mail_client.py.
Mỗi lỗ hổng đối chiếu mã T trong threat_model.md.

## 1. agent/tools.py — query_db(sql)
**Lỗ hổng:** nhận nguyên văn câu SQL do model tự sinh, không kiểm tra bảng/cột
truy cập. Model có thể (bị lừa) truy vấn bất kỳ bảng nào, kể cả salaries,
customers, api_keys.
**Mã đe dọa:** T2 (Excessive Agency — truy vấn cột nhạy cảm không liên quan).
**Hiện trạng giảm nhẹ:** kết nối mở ở chế độ chỉ đọc (mode=ro) nên không thể
sửa/xóa dữ liệu — nhưng KHÔNG ngăn được việc ĐỌC dữ liệu mật.
**Dự kiến khắc phục:** Guardrails lớp ② — allowlist bảng/cột được phép truy
vấn theo ngữ cảnh (tuần 6).

## 2. agent/tools.py — send_email(to, subject, body)
**Lỗ hổng:** gửi tới bất kỳ địa chỉ nào model đưa ra, không kiểm tra miền
người nhận.
**Mã đe dọa:** T3 (gửi email tới địa chỉ ngoài allowlist).
**Dự kiến khắc phục:** Guardrails lớp ② — allowlist miền người nhận (tuần 6).

## 3. agent/tools.py — read_email()
**Lỗ hổng:** đưa NGUYÊN VĂN nội dung email (đã làm sạch HTML cơ bản) vào
ngữ cảnh model, không phân biệt với mệnh lệnh người dùng, không gắn nhãn
nguồn không tin cậy.
**Mã đe dọa:** T1 (ghi đè chỉ thị), T6 (chỉ thị giấu qua HTML/ký tự ẩn) —
_làm sạch hiện tại chỉ bỏ thẻ, CHƯA chặn nội dung chỉ thị ẩn trong văn bản
thường_.
**Dự kiến khắc phục:** Guardrails lớp ① — spotlighting/delimiter, lọc mẫu
chỉ thị đáng ngờ (tuần 6).

## 4. agent/core.py — vòng lặp run_agent
**Lỗ hổng:** không có điểm dừng nào trước khi thực thi công cụ; mọi lời
gọi đều ALLOW mặc định (tham số policy chưa được dùng ở tuần 1-3).
**Mã đe dọa:** T5 (hành động rủi ro cao chạy mà không ai biết).
**Dự kiến khắc phục:** Guardrails lớp ④ — Human-in-the-Loop (tuần 7).

## 5. agent/core.py — cờ state["tainted"]
**Lỗ hổng:** đã đặt True sau read_email nhưng CHƯA được dùng để hạn chế
hành động nào. Hiện tại chỉ là biến chết.
**Mã đe dọa:** T2, T3, T7 (chuỗi tấn công qua nhiều email).
**Dự kiến khắc phục:** Guardrails lớp ② sẽ đọc cờ này để khóa công cụ nhạy
cảm khi ngữ cảnh đã nhiễm nội dung ngoài (tuần 6-7).

## 6. lab/mail_client.py — route_server
**Lỗ hổng:** không phải lỗ hổng của agent, mà là QUY TẮC LAB: định tuyến
dựa hoàn toàn vào domain @company.test, agent không biết và không kiểm
soát được việc này — đúng ý đồ thiết kế (mô phỏng "gửi email" như thật).
**Ghi chú:** không cần khắc phục, đây là biên giả lập của môi trường.

## 7. Phát hiện hành vi (không phải lỗi code, nhưng là rủi ro vận hành)
- Excessive Agency tự phát của dolphin-llama3:8b (tự gửi email dù không
  được yêu cầu) — không do lỗi code, là đặc tính mô hình.
- "Giả lập tuân thủ" của llama3.2:3b (bịa kết quả công cụ mà không gọi
  thật) — rủi ro cho mọi lớp phòng thủ dựa trên lời khai của model; lý do
  ta dùng leak_checker độc lập thay vì tin lời agent.

## Kết luận
Agent v0 (tuần 1-3) không có cơ chế kiểm soát nào ở tầng ứng dụng — mọi
công cụ ALLOW mặc định. Đây chính là baseline "dễ bị tấn công" đúng như
thiết kế của đề cương (Bước 1, mục 4.2). Bảng trên là bản đồ cho 4 lớp
Guardrails sẽ cài ở tuần 6-7.