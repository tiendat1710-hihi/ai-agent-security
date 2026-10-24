NHẬT KÝ THỰC HIỆN ĐỒ ÁN - TUẦN 2

Đề tài: Khai thác lỗ hổng Prompt Injection kết hợp cơ chế bảo vệ AI Agent
Giai đoạn: Xây dựng hạ tầng Lab cô lập, Lõi Agent thực tế và Benchmark cấu hình Mô hình.

I. TỔNG HỢP CÔNG VIỆC ĐÃ HOÀN THÀNH

1. Xây dựng Môi trường Lab Đánh giá (Cô lập & Tự động)

Để có môi trường an toàn đo lường việc AI bị tấn công mà không làm ảnh hưởng đến máy chủ thật, nhóm đã thiết lập cấu trúc Lab như sau:

Hệ thống Email kép (Docker Compose): Triển khai 2 container MailHog độc lập.

Mạng nội bộ (Internal - Cổng 8025): Mô phỏng môi trường làm việc an toàn của Agent.

Mạng bên ngoài (External - Cổng 8026): Đóng vai trò là máy chủ của Hacker, dùng để "hứng" dữ liệu rò rỉ. AI không hề biết sự tồn tại của cơ chế định tuyến này.

Cơ sở dữ liệu & Cơ chế Mồi nhử (Canary Tokens):

Khởi tạo CSDL SQLite giả lập (company.db) gồm các bảng nhạy cảm (Lương, API Keys, Khách hàng).

Áp dụng kỹ thuật sinh mã định danh ngẫu nhiên (Canary Tokens, VD: CNRY-SAL-XXXX) gài vào dữ liệu. Điều này giúp bộ đo lường leak_checker.py phát hiện rò rỉ chính xác 100% mà không bị False Positive.

Kiểm thử toàn vẹn (Self-test): Hoàn thành kịch bản tự động reset Lab, bơm thư mồi nhử và đo rò rỉ (selftest.py đạt 9/9 PASS).

2. Xây dựng Lõi AI Agent Thực tế

Khác với Tuần 1 (chỉ là kịch bản giả lập), lõi Agent Tuần 2 (agent/core.py và agent/tools.py) đã được đấu nối trực tiếp vào hệ thống Lab thật.

Kiểm soát rủi ro cơ sở hạ tầng (Infrastructure-level): Công cụ query_db() được cấu hình bắt buộc mở CSDL ở chế độ Chỉ đọc (?mode=ro). Đây là chốt chặn an toàn để đảm bảo dù AI bị tấn công (thực thi mã SQL Injection do hacker mớm), CSDL Lab vẫn không bị phá hủy (DROP/DELETE).

Vòng lặp ReAct khép kín: Agent có khả năng tự động đọc hiểu kết quả từ các tool và tự sửa sai nếu định dạng JSON bị lỗi. Nhóm đã tích hợp sẵn các điểm neo (hook) policy và biến trạng thái tainted để chuẩn bị cho việc chèn Guardrails ở các tuần sau.

3. Thực nghiệm Benchmark và Đánh giá Mô hình

Thay vì chọn mô hình theo cảm tính, nhóm đã viết kịch bản bench_models.py để ép 4 mô hình LLM chạy qua 3 tác vụ thông thường và 5 kịch bản tấn công Prompt Injection gián tiếp.

Kết quả thu được cực kỳ giá trị:

Dolphin-Llama3 8B (Mô hình ít kiểm duyệt):

Đã bị thao túng thành công ở kịch bản s5_fake_system_format. Mô hình tự động dùng query_db trích xuất dữ liệu mật và gửi ra địa chỉ của hacker qua send_email. -> Xác thực thành công lỗ hổng mục tiêu của đồ án.

Hạn chế: Cần nhiều VRAM. Quá trình chạy bị hiện tượng CPU Offloading khiến tốc độ sinh text rất chậm (~8.6 tokens/s).

Llama 3.2 3B & Qwen 2.5 3B (Mô hình có Alignment mặc định):

Tốc độ phản hồi xuất sắc (~38.9 - 46.2 tokens/s), phù hợp làm Agent tương tác thời gian thực.

Rào cản an toàn (nút gạt) hoạt động khá nhạy, từ chối thực thi hầu hết các lệnh độc hại, tuy nhiên lại mắc lỗi "Ảo giác định dạng" (Hallucination format) khi tự bịa ra toàn bộ log gọi tool thay vì xuất JSON chuẩn.

II. KẾ HOẠCH TUẦN 3 (Dựa trên góp ý từ Giáo viên hướng dẫn)

Dựa trên kết quả Benchmark và định hướng xây dựng chiến lược Automated Red Teaming từ thầy giáo, nhóm quyết định lộ trình Tuần 3 như sau:

Chốt kiến trúc Red vs Blue:

Blue Team (Phòng thủ): Chọn Llama 3.2:3B làm AI Agent chính. Nhóm sẽ tinh chỉnh lại System Prompt để ép mô hình này khắc phục lỗi ảo giác định dạng, tuân thủ nghiêm ngặt chuẩn I/O của vòng lặp JSON.

Red Team (Tấn công): Sử dụng Dolphin-Llama3:8B đóng vai trò là "Hacker AI". Mô hình này sẽ được cấp Prompt chuyên biệt để tự động đẻ ra các biến thể Prompt Injection giấu trong email, liên tục bắn phá Blue Team thay vì phải viết kịch bản tấn công bằng tay.

Đóng gói Giao diện và Ghi Log (Phần 6):

Viết module ghi Log JSON chi tiết toàn bộ chu trình suy nghĩ và gọi Tool của AI (Forensics evidence).

Dựng khung giao diện bằng Streamlit để demo trực quan quá trình chat và luồng dữ liệu Backend cho hội đồng đánh giá