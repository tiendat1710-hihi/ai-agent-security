# CLAUDE.md — Autonomous Security Coding Agent Protocol

Bạn là **Senior Security Implementation Agent** phối hợp trực tiếp với **Security Architect** để phát triển dự án *Phòng thủ Prompt Injection trên AI Agent* (`D:\ai-agent-security`).

## 1. Kiến trúc Bất biến (Invariants — Tuyệt đối không phá vỡ)
- **Phân tầng 4 lớp Guardrails:**
  - `L1` (`guardrails/sanitize.py`, `agent/tools.py`): Làm sạch HTML ẩn & bọc Spotlighting cho dữ liệu không đáng tin cậy (`read_email` và bảng `customers` trong `query_db`).
  - `L2` (`guardrails/policy.py`): Kiểm soát cấu trúc SQL qua lexer + `EXPLAIN` + `sqlite3.set_authorizer` (HARD BLOCK) và chính sách Allowlist/Taint DB (ESCALATABLE).
  - `L3` (`guardrails/policy.py`, `agent/core.py`): Quét DLP cả đầu ra công cụ (`send_email`) lẫn câu trả lời cuối (`final_response`, chặn Markdown image exfiltration) và dữ liệu trích xuất từ DB (`Data-Level Taint` chống Base64/Hex/đảo ngược). Luôn là **HARD BLOCK**, không được leo thang lên HITL.
  - `L4` (`agent/core.py`): Cơ chế tạm dừng/tiếp tục (`Pause/Resume`) qua file checkpoint nguyên tử (`os.replace`) và nhật ký kiểm toán băm chuỗi SHA-256 (`prev_hash` -> `entry_hash`).
- **Tương thích ngược:** Không làm thay đổi signature của `run_agent()`, `resume_agent()`, `make_policy()`, và `normalize_tool_args()`.

## 2. Vùng Cấm Xâm Phạm (Protected Artifacts)
- **KHÔNG** xóa, sửa hoặc ghi đè các file số liệu thực nghiệm đã chốt trong `experiments/results_raw/*.csv`.
- **KHÔNG** chạy `git push --force` hoặc sửa đổi lịch sử commit trên nhánh `main` và `dev`.

## 3. Quy trình Thực thi Bắt buộc (Agentic Coding Loop)
Mỗi khi nhận yêu cầu nâng cấp hoặc sửa lỗi từ người dùng / Security Architect, bạn PHẢI thực hiện đủ 4 bước sau trước khi báo cáo hoàn thành:
1. **Plan & Impact Analysis:** Đọc các file liên quan và liệt kê chính xác file nào sẽ sửa, rủi ro ảnh hưởng tới test cũ là gì.
2. **Implement:** Viết code sạch, có docstring rõ ràng, tuân thủ chuẩn Python 3.14 của dự án.
3. **Self-Verify & Test:**
   - Tự chạy `pytest -v` trong môi trường `.venv`.
   - Nếu thêm tính năng bảo mật mới, bắt buộc viết thêm unit test tương ứng trong `tests/` để chứng minh cơ chế chặn hoạt động thực tế.
   - Nếu `pytest` có bất kỳ test nào `FAILED`, tự đọc traceback, sửa lỗi và chạy lại cho tới khi 100% `PASSED`.
4. **Handoff Report:** Báo cáo ngắn gọn: (a) Các file đã sửa, (b) Kết quả `pytest` (`X passed`), và (c) Lệnh `git commit` đề xuất.