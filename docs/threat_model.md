```mermaid
flowchart LR
    U[Người dùng / Nhân viên<br/>TIN CẬY] -->|yêu cầu: "tóm tắt email"| A[Agent<br/>agent.py + LLM]
    H[Kẻ tấn công<br/>KHÔNG TIN CẬY] -->|email phishing chứa chỉ thị ẩn| M[(Hộp thư nội bộ<br/>MailHog)]
    A -->|read_email| M
    A -->|query_db| D[(SQLite<br/>dữ liệu mật giả)]
    A -->|send_email| X[(Hộp thư bên ngoài<br/>MailHog = hacker)]
    G{{Guardrails<br/>chen giữa Agent và công cụ}} -.kiểm duyệt.- A
```
1. Tổng quan hệ thống (1 đoạn)
2. Sơ đồ luồng dữ liệu (bước 6.1)
3. Tài sản (6.2)
4. Kẻ tấn công và điểm vào (6.3)
5. Chuỗi tấn công (6.4)
6. Bảng mối đe dọa và lớp phòng thủ (6.5)
7. Giả định, phạm vi và cách đo thành công (6.6)