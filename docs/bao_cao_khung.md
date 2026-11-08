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

## Nhật ký tuần 2

**Đã xong:**
- Hợp đồng kỹ thuật `config.py` + `docs/interfaces.md` (cổng dịch vụ, schema
  DB, quy cách canary, định dạng log, tên công cụ) — nền tảng cho mọi tuần sau.
- Lab giả lập: Docker Compose 2 MailHog (nội bộ 1025/8025, "hacker" 1026/8026).
- Dữ liệu giả SQLite có canary (CNRY-...), sinh lại được bằng 1 lệnh, seed cố
  định (manifest hash giống nhau giữa các lần chạy).
- Bộ đo lường độc lập với agent: `leak_checker.py` (trọng tài rò rỉ),
  `mail_client.py`, `reset_lab.py`; `selftest.py` đạt 8/8.
- Lõi agent thật (`agent/core.py`, `agent/tools.py`), không dùng framework,
  có sẵn chỗ cắm Guardrails (`policy()`) và cờ `tainted`.
- Benchmark 3 mô hình với 5 email sàng lọc (2 nhóm: có alignment / gỡ kiểm
  duyệt), lặp 3 lần, nhiệt độ 0.5:
  - dolphin-llama3:8b (gỡ kiểm duyệt): rò rỉ dữ liệu thật 6/15 lượt (~40%).
  - llama3.2:3b (có alignment mặc định): KHÔNG rò rỉ dữ liệu thật, nhưng
    gửi thư trái phép ra ngoài 10/15 lượt — chứng minh "nút gạt" không
    chặn được việc làm theo chỉ thị trong email, chỉ là mô hình nhỏ chưa đủ
    năng lực chép dữ liệu thật vào thư.
  - qwen2.5:3b: dữ liệu chưa đủ tin cậy (phần lớn lượt không gọi công cụ nào),
    cần điều tra thêm.
- Khung giao diện Streamlit (Chat / Nhật ký tool call / Đối chiếu) và bộ ghi
  log JSON Lines theo đúng hợp đồng.

**Quyết định mới trong tuần:**
- Chọn hướng sinh payload nâng cao: Attacker Agent (mô hình tự sinh/sửa
  payload dựa trên kết quả đo), dự kiến code ở tuần 4-5 (xem mục 6 của
  `docs/khao_sat_guardrails.md`). Không vi phạm ràng buộc "không fine-tune".
- Giữ cấu trúc 2 nhóm mô hình (có alignment / gỡ kiểm duyệt) để chứng minh
  lỗ hổng Indirect Prompt Injection không phụ thuộc việc gỡ kiểm duyệt.
- Tạm gác mistral:7b khỏi benchmark chính (lỗi vận hành, chưa rõ nguyên nhân).

**Vướng mắc / câu hỏi cho thầy:**
- [ĐIỀN nếu có — ví dụ: nhóm có cần đo thêm mô hình qua API để đối chiếu
  không, hay 3 mô hình local là đủ phạm vi?]

**Kế hoạch tuần 3:** hoàn thiện agent chính thức (ghép log thật vào mọi
lượt chạy), đo baseline tác vụ hợp lệ trên 30 email bình thường, chuẩn bị
nền cho vòng 1 tấn công ở tuần 4.
## Nhật ký tuần 3
- Hoàn thiện agent/core.py: log mặc định qua RunLogger, xử lý rõ "HET SO
  BUOC" khi vượt max_steps.
- Soạn 30 email bình thường, 6 nhóm (notice, forward, lookup,
  complex_format, html, multistep), mỗi email có tiêu chí đạt/trượt rõ.
- Đo baseline (temp 0.0, 1 lần/email):
  qwen2.5:3b 29/30 (96.7%), dolphin-llama3:8b 15/30 (50%),
  llama3.2:3b 14/30 (46.7%).
- Phát hiện quan trọng: hai kiểu lỗi khác nhau ở nhóm chỉ-tóm-tắt:
  (1) Excessive Agency của dolphin (tự gửi email thừa);
  (2) "gia lap tuan thu" cua llama3.2 (bia ket qua cong cu ma khong goi
  that - da xac minh qua transcript raw).
- Ghép log JSON thật và bảng baseline vào Streamlit (tab Nhật ký, tab
  Đối chiếu).
- Rà soát mã nguồn agent: 5 lỗ hổng/thiếu kiểm soát, đối chiếu T1-T8.
- Thiết kế Attacker Agent (dùng dolphin-llama3:8b làm bên tấn công,
  lặp sinh-chạy-đo-sửa dựa trên leak_checker) để triển khai tuần 4,
  theo quyết định chọn hướng sinh payload số 3.