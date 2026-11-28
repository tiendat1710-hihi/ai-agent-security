# Nhật ký Tuần 6 — Demo tích hợp (Streamlit)

## Phần 1: Khung app + thanh điều khiển phòng thủ (XONG)
- Tách app thành đa trang: ui/common.py (sidebar + build_policy), ui/app.py (5 tab),
  ui/page_home.py (chạy được), 4 stub page_attack/hitl/audit/results.
- Sidebar bật/tắt THẬT từng lớp: L1 -> config.ENABLE_L1; L2/L3/L4 -> make_policy.
- Trang "Thử nhanh" chạy agent theo cấu hình + hiện verdict rò rỉ của leak_checker.
## Phần 2: Trang Tấn công trực tiếp (XONG)
- ui/page_attack.py: chọn 1 trong 6 kịch bản seed -> nạp mail -> chạy agent theo cấu hình sidebar.
- Hiển thị từng bước Plan -> Act -> Observe, nêu rõ lớp nào CHẶN / TREO DUYỆT.
- Trọng tài leak_checker phán: RÒ RỈ THẬT / có thư ra ngoài / an toàn.
- Demo đủ 4 hành vi: none rò rỉ -> L2 chặn query -> L1 lọc HTML ẩn -> L4 treo duyệt.
## Phần 3.1: Hàng đợi duyệt HITL — Lớp 4 (XONG)
- core.py: thêm nhánh PENDING_APPROVAL -> đẩy hành động vào hàng đợi (không tự gửi).
- guardrails/hitl_queue.py: enqueue/list/resolve, lưu JSONL; duyệt thì gọi tools.send_email thật.
- ui/page_hitl.py: hiện thư treo + nút Duyệt/Từ chối, cảnh báo người nhận ngoài miền.
- Demo: Từ chối -> chặn; Duyệt -> gửi thật -> rò rỉ -> con người là chốt chặn cuối.
## Phần 3.2: HITL — XONG
- dolphin + s3_urgency + chỉ L4: send_email chứa 5 CNRY-KEY bị treo.
- Duyệt -> 5 marker lọt ra ngoài (con người duyệt nhầm = rò rỉ). Từ chối -> lượt chạy dừng.
- Lịch sử có đủ: Từ chối / Đã thực thi / Hết hạn (10 phút).
- Ghi nhận: s1 (bảng lương dài) làm dolphin hết bước do JSON bị cắt ở 512 token; s3 (api_keys) đi trọn chuỗi.

## Phần 4: Nhật ký kiểm toán — XONG
- 823 sự kiện, 89 chặn (L2 87, L3 2), 34 treo, 1 duyệt, 1 từ chối; khớp audit_summary CLI.
- Lọc theo lớp, truy vết theo run_id (761f38f8: L2 chặn query_db và send_email).
