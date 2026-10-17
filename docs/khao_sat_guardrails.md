# Khảo sát kỹ thuật Guardrails và DLP cho AI Agent

## 1. Vấn đề cần giải quyết
Trong agent của nhóm, nội dung email (không tin cậy) và mệnh lệnh người dùng
(tin cậy) cùng nằm trong một ngữ cảnh văn bản. Mô hình ngôn ngữ không có cơ chế
cứng để phân biệt hai loại này. Vì vậy phòng thủ không thể chỉ dựa vào việc
"dặn mô hình đừng làm theo", mà phải đặt các chốt kiểm soát ở BÊN NGOÀI mô hình.
Đây là hướng "Guardrails ngoài mô hình" của đề tài, không cần huấn luyện lại.

## 2. Các nhóm kỹ thuật đã khảo sát

### 2.1. Gắn nhãn và cách ly nội dung không tin cậy (Spotlighting)
- Ý tưởng: đánh dấu rõ phần nào là dữ liệu bên ngoài để mô hình dễ phân biệt.
- Các biến thể: dùng ký tự phân cách (delimiter) bao quanh nội dung email;
  chèn ký tự đánh dấu xen kẽ vào văn bản (datamarking); mã hóa nội dung (ví dụ base64).
- Nguồn tham khảo: Hines et al. (Microsoft, 2024), bài về Spotlighting.
- Ưu điểm: dễ cài, gần như không tốn thời gian chạy.
- Hạn chế: chỉ GIẢM xác suất bị thao túng, không loại bỏ hoàn toàn; mô hình nhỏ
  có thể vẫn làm theo. [ĐIỀN: kết quả đo thực tế của nhóm ở tuần 8]
- Dự định dùng ở: lớp ①.

### 2.2. Làm sạch và phát hiện chỉ thị đáng ngờ ở đầu vào
- Làm sạch: loại thẻ HTML ẩn, chú thích HTML, ký tự không hiển thị (zero-width),
  chuẩn hóa Unicode.
- Phát hiện: luật/biểu thức chính quy (cụm "ignore previous instructions",
  yêu cầu gửi dữ liệu tới địa chỉ lạ...); hoặc mô hình phân loại nhỏ chuyên phát hiện
  prompt injection (có một số mô hình mã nguồn mở và dịch vụ thương mại).
- Ưu điểm: chặn sớm trước khi nội dung tới mô hình.
- Hạn chế: luật dễ bị né bằng cách diễn đạt lại; mô hình phân loại có thể chặn nhầm
  và tốn thêm thời gian.
- Dự định dùng ở: lớp ① (luật tự viết trước; mô hình phân loại chỉ cân nhắc nếu đủ thời gian).

### 2.3. Đặc quyền tối thiểu và chính sách công cụ
- Ý tưởng: kể cả khi mô hình bị lừa, hành động nguy hiểm vẫn bị từ chối ở tầng code.
- Các biện pháp: danh sách miền người nhận được phép (allowlist); truy vấn chỉ đọc;
  cấm hoặc che cột nhạy cảm; giới hạn số lần gọi công cụ.
- Khóa theo "taint": khi ngữ cảnh đã chứa nội dung từ nguồn không tin cậy
  (email bên ngoài), các công cụ nhạy cảm như gửi thư hoặc truy vấn bảng lương
  bị khóa hoặc phải chờ duyệt.
- Nguồn tham khảo: các bài về mẫu thiết kế bảo vệ agent trước prompt injection
  và các bài của Simon Willison (khái niệm "lethal trifecta": dữ liệu riêng tư +
  nội dung không tin cậy + khả năng gửi ra ngoài).
- Ưu điểm: quyết định bằng code nên ổn định, không phụ thuộc mô hình.
- Hạn chế: quá chặt thì làm giảm tính hữu dụng của agent.
- Dự định dùng ở: lớp ② (lớp quan trọng nhất của đồ án).

### 2.4. DLP đầu ra (Data Loss Prevention)
- Ý tưởng: quét nội dung trước khi gửi ra ngoài để phát hiện dữ liệu mật.
- Kỹ thuật: biểu thức chính quy cho mẫu dữ liệu nhạy cảm (số định danh, khóa API,
  số tiền lương); đối chiếu với danh sách giá trị mật đã biết; chuỗi canary đặt sẵn
  trong dữ liệu giả để phát hiện rò rỉ.
- Có sẵn công cụ mã nguồn mở nhận diện thông tin nhạy cảm và bí mật; nhóm dự định
  tự viết luật đơn giản để kiểm soát được hành vi. [ĐIỀN: nếu có dùng thêm thư viện nào]
- Ưu điểm: chốt chặn cuối cùng, bắt được cả khi các lớp trước bị vượt qua.
- Hạn chế: kẻ tấn công có thể yêu cầu mã hóa hoặc chia nhỏ dữ liệu để né mẫu.
- Dự định dùng ở: lớp ③.

### 2.5. Người duyệt (Human-in-the-Loop) và nhật ký kiểm toán
- Ý tưởng: hành động rủi ro cao dừng lại chờ người xác nhận; mọi lời gọi công cụ
  đều được ghi lại cùng quyết định và lý do.
- Ưu điểm: giữ quyền quyết định cuối cùng cho con người; có bằng chứng truy vết.
- Hạn chế: có thể gây "mệt mỏi cảnh báo" nếu hỏi quá nhiều, nên chỉ áp dụng cho
  hành động rủi ro cao.
- Dự định dùng ở: lớp ④.

## 3. Bảng tổng hợp
| Kỹ thuật | Chặn được mối đe dọa (theo threat model) | Lớp | Độ khó cài | Ghi chú |
|---|---|---|---|---|
| Spotlighting | T1 | ① | Thấp | Giảm, không loại trừ |
| Làm sạch HTML/ký tự ẩn | T6 | ① | Thấp | Cần khi kẻ tấn công che giấu chỉ thị |
| Phát hiện bằng luật | T1, T7 | ① | Trung bình | Dễ chặn nhầm |
| Allowlist người nhận | T3 | ② | Thấp | Hiệu quả cao |
| Truy vấn chỉ đọc/che cột | T2 | ② | Trung bình | Cần danh sách cột nhạy cảm |
| Khóa công cụ theo taint | T2, T3, T7 | ② | Trung bình | Cần cờ trạng thái trong agent |
| DLP đầu ra | T4 | ③ | Trung bình | Dùng canary để kiểm thử |
| Duyệt + audit log | T5, T8 | ④ | Trung bình | Cần giao diện Streamlit |

## 4. Kết luận của khảo sát
Không có biện pháp nào đủ một mình. Nhóm áp dụng phòng thủ nhiều lớp:
các lớp chạy bằng code (②, ③, ④) đóng vai trò chốt cứng, lớp ① làm giảm xác suất
tấn công tới được mô hình. Mức hiệu quả từng lớp sẽ được đo bằng ablation ở tuần 8.

## 5. Tài liệu tham khảo
[ĐIỀN: liệt kê đúng các bài bạn đã đọc ở Phần 5, kèm năm và tác giả]