# BÁO CÁO ĐỒ ÁN CHUYÊN NGÀNH AN NINH MẠNG
Đề tài: Đánh giá rủi ro Prompt Injection trên kiến trúc AI Agent
Nhóm: [ĐIỀN tên thành viên, vai trò]    Giảng viên hướng dẫn: [ĐIỀN]

## Chương 1. Giới thiệu
1.1. Lý do chọn đề tài (lấy từ đề cương)
1.2. Mục tiêu và phạm vi
1.3. Ràng buộc an toàn và đạo đức
[Trạng thái: bản nháp từ đề cương, hoàn thiện tuần 9]

## Chương 2. Cơ sở và khảo sát
2.1. AI Agent và tool calling
2.2. Direct và Indirect Prompt Injection
2.3. OWASP Top 10 cho ứng dụng LLM (ghi rõ phiên bản)
2.4. Các kỹ thuật Guardrails và DLP (lấy từ khao_sat_guardrails.md)
[Trạng thái: tuần 1 đã có nội dung gốc ở docs/ghi_chu_owasp.md và docs/khao_sat_guardrails.md]

## Chương 3. Thiết kế hệ thống
3.1. Kiến trúc tổng thể và threat model (lấy từ threat_model.md)
3.2. Môi trường lab (Docker, MailHog, SQLite, dữ liệu giả có canary)   [tuần 2]
3.3. Agent tự xây dựng không dùng framework (vòng lặp Plan-Act-Observe)  [tuần 3]
3.4. Lựa chọn mô hình ngôn ngữ và kết quả benchmark                      [tuần 2]

## Chương 4. Tấn công (Red Team)
4.1. Sáu nhóm kỹ thuật và thư viện 30 payload                           [tuần 4]
4.2. Kịch bản tấn công end-to-end                                        [tuần 5]
4.3. Kết quả ASR baseline và phân tích                                   [tuần 5]

## Chương 5. Phòng thủ (Blue Team)
5.1. Bốn lớp Guardrails                                                  [tuần 6-7]
5.2. Tấn công thích ứng vào Guardrails                                   [tuần 7]

## Chương 6. Đánh giá
6.1. Phương pháp đo (ASR, chặn nhầm, hoàn thành tác vụ, độ trễ)
6.2. Kết quả trước và sau phòng thủ, ablation                            [tuần 8]
6.3. Hạn chế

## Chương 7. Kết luận và hướng phát triển

## Phụ lục
A. Hướng dẫn cài đặt   B. Danh sách payload   C. Dữ liệu thô