# Nhật ký Đồ án - Tuần 3: Tối ưu Agent & Thiết lập Baseline Đo lường

## 1. Mục tiêu Tuần 3
Sau khi dựng thành công kiến trúc cơ sở ở Tuần 2, mục tiêu của Tuần 3 là tinh chỉnh Llama 3.2 3B thành một Blue Team Agent hoạt động ổn định và thiết lập mốc đối chứng (Baseline) hiệu năng trước khi bị tấn công. Trọng tâm:
- Khắc phục lỗi "ảo giác định dạng JSON" của LLM.
- Tự động hóa cơ chế ghi log (Forensics).
- Đo lường mức độ hoàn thành tác vụ trên các email bình thường (Benign).

## 2. Công việc đã thực hiện
### 2.1. Nâng cấp Lõi Điều phối (agent/core.py)
Để đảm bảo quá trình đo lường không bị sai lệch, mã nguồn lõi đã được tái cấu trúc:
- **Default Logging (Hộp đen tự động):** Chuyển cơ chế ghi log từ thủ công sang mặc định. Class `RunLogger` được gắn chết vào vòng lặp ReAct, đảm bảo 100% các phiên chạy đều sinh file `.jsonl`, lưu vết mọi Tool Call và độ trễ (Latency).
- **Graceful Degradation (Xử lý kẹt vòng lặp):** Bổ sung cơ chế ngắt an toàn (`for...else`) khi Agent bị "ảo giác" dẫn đến cạn kiệt 6 vòng lặp `max_steps`. Log sẽ ghi nhận trạng thái `(HET SO BUOC)` thay vì sập hệ thống.

### 2.2. Prompt Engineering (Chữa lỗi Ảo giác Định dạng)
Dữ liệu Tuần 2 cho thấy LLM thường xuyên lờ đi định dạng JSON yêu cầu. Để khắc phục, System Prompt đã được gia cố bằng các "Luật Thép" (Critical Rules):
- Cấm sử dụng cú pháp markdown (```json).
- Cấm đưa ra các văn bản đàm thoại hoặc giải thích rườm rà.
- Bắt buộc đầu ra phải là một JSON Object duy nhất và hoàn chỉnh.

### 2.3. Kiểm thử và Đối chứng (Baseline)
- Đã tạo thành công 30 kịch bản email bình thường (phân bổ thành 6 nhóm, mỗi nhóm 5 biến thể) làm dữ liệu đối chứng.
- Thực hiện chạy Benchmark các mô hình trên tập dữ liệu này. Kết quả Baseline thu được sẽ là thước đo (KPI) để tính toán "độ sụt giảm hiệu năng" khi lắp đặt Guardrails ở Tuần 8 (Mục tiêu: Giảm không quá 10%).

## 3. Đánh giá & Kết luận
Agent `llama3.2:3b` hiện đã hoạt động mượt mà, định dạng trả về chuẩn xác, không còn lỗi gọi Tool. Hệ thống log đã sẵn sàng thu thập số liệu quy mô lớn. 
Cơ sở hạ tầng và Agent phòng thủ (Blue Team) đã hoàn thiện 100%, sẵn sàng bước vào Pha Tấn Công (Red Teaming) ở các tuần tiếp theo.