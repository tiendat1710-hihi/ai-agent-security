## Nhật ký tuần 1 (số liệu đã đo)
- Môi trường: Windows, Python 3.12.3, Ollama, RTX 2050 4GB, RAM 32GB; model lưu tại D:\OllamaModels
- Mô hình thử: dolphin-llama3:8b (5.4 GB; 56%/44% CPU/GPU; context 4096)
- Tốc độ sinh chữ: khoảng 12 tokens/s
- Định dạng JSON gọi công cụ: hợp lệ 3/3 bài thử
- Quan sát: mô hình tự gửi email và truy vấn database dù chỉ được yêu cầu tóm tắt
  (Excessive Agency tự phát) → phải định nghĩa "hoàn thành tác vụ hợp lệ" gồm
  làm đúng việc VÀ không làm hành động thừa
- Quan sát: mô hình trả lời tiếng Việt kém → system prompt và payload viết tiếng Anh
- Quyết định: không dùng LangChain/LangGraph; tự code agent theo yêu cầu của thầy
- Quyết định: dùng chuỗi canary trong dữ liệu giả để đo ASR tự động