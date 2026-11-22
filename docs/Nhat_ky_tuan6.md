# Nhật ký Tuần 6 — Demo tích hợp (Streamlit)

## Phần 1: Khung app + thanh điều khiển phòng thủ (XONG)
- Tách app thành đa trang: ui/common.py (sidebar + build_policy), ui/app.py (5 tab),
  ui/page_home.py (chạy được), 4 stub page_attack/hitl/audit/results.
- Sidebar bật/tắt THẬT từng lớp: L1 -> config.ENABLE_L1; L2/L3/L4 -> make_policy.
- Trang "Thử nhanh" chạy agent theo cấu hình + hiện verdict rò rỉ của leak_checker.
