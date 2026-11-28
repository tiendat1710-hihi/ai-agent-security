# AI Agent Security Lab

Đồ án thực nghiệm về rủi ro prompt injection gián tiếp trên AI Agent. Agent nhận yêu cầu, đọc email, truy vấn SQLite và có thể gửi thư. Lab giúp quan sát mức giảm rủi ro của từng lớp phòng thủ và ảnh hưởng đến khả năng hoàn thành tác vụ hợp lệ.

Toàn bộ dữ liệu trong SQLite là dữ liệu giả. Hai hộp thư MailHog chạy cục bộ và giữ thư trong lab. Chế độ `none` tắt cả bốn lớp để làm đối chứng. Giữ các dịch vụ trong môi trường thử nghiệm.

## Khởi chạy trên Windows

Chuẩn bị Python 3.12, Docker Desktop với Docker Compose và [Ollama](https://ollama.com/). Mở PowerShell tại thư mục chứa `README.md`.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install "streamlit>=1.66,<2" requests pandas altair
docker compose up -d
ollama pull qwen2.5:3b
```

`qwen2.5:3b` là lựa chọn mặc định trên giao diện. Tải thêm `llama3.2:3b` hoặc `dolphin-llama3:8b` nếu cần chọn chúng từ thanh bên.

Nếu chưa có cơ sở dữ liệu, tạo dữ liệu mẫu bằng lệnh dưới đây. Lệnh này tạo lại dữ liệu SQLite và tệp dấu vết nhạy cảm của lab.

```powershell
.\.venv\Scripts\python.exe -m lab.seed_data
.\.venv\Scripts\python.exe -m streamlit run ui/app.py --server.address 127.0.0.1
```

| Dịch vụ | Địa chỉ | Vai trò |
| --- | --- | --- |
| Streamlit | [localhost:8501](http://localhost:8501/) | Giao diện demo |
| Ollama | `localhost:11434` | Chạy mô hình cục bộ |
| MailHog nội bộ | [localhost:8025](http://localhost:8025/) | Hộp thư agent đọc và nhận thư nội bộ, SMTP cổng 1025 |
| MailHog bên ngoài | [localhost:8026](http://localhost:8026/) | Hộp thư kiểm tra thư ngoài miền, SMTP cổng 1026 |

Để thử tóm tắt thư, nạp bộ email hợp lệ bằng `.\.venv\Scripts\python.exe -m lab.load_mail attacks/benign`. Nút **Reset Lab** xóa thư trong cả hai hộp thư và tạo lại cơ sở dữ liệu, vì vậy hãy lưu lại bằng chứng demo cần giữ trước khi dùng.

## Bốn lớp phòng thủ

| Lớp | Hành vi |
| --- | --- |
| **L1 · Làm sạch email** | Lọc phần HTML ẩn và đánh dấu nội dung email là dữ liệu không đáng tin. |
| **L2 · Giới hạn công cụ** | Kiểm tra miền người nhận. Sau khi agent đọc email, dùng SQLite để kiểm tra bảng mà truy vấn thực sự truy cập. |
| **L3 · DLP** | Chặn gửi thư nếu tiêu đề hoặc nội dung khớp các mẫu dữ liệu nhạy cảm được cấu hình. |
| **L4 · Người duyệt** | Giữ thư ngoài miền để người dùng quyết định. Khi bật cùng L2, một số truy vấn bảng nhạy cảm cũng cần duyệt. Agent tiếp tục theo cấu hình lúc bắt đầu lượt. |

## Xem demo và kiểm tra HITL

- **Thử nhanh** gửi yêu cầu trực tiếp cho agent và xem hoạt động trong hai hộp thư.
- **Tấn công trực tiếp** hiển thị diễn biến của kịch bản lab, quyết định Guardrails và kết quả quan sát trong hộp thư ngoài.
- **Hàng đợi duyệt** hiển thị nội dung cần duyệt, nguồn email nếu có và lịch sử xử lý. Yêu cầu chờ tối đa 10 phút.
- **Nhật ký kiểm toán** lọc theo lớp, quyết định, mô hình hoặc mã lượt chạy.
- **Bảng kết quả** đọc các ma trận ASR và tệp Utility đã lưu.

Để trình diễn hai nhánh HITL với thư kiểm tra vô hại:

1. Chỉ bật **L4**. Trong **Thử nhanh**, yêu cầu gửi một thư kiểm tra đến `partner@example.test`, với tiêu đề dễ nhận ra như `HITL thử từ chối`.
2. Vào **Hàng đợi duyệt** và bấm **Từ chối**. Tìm tiêu đề đó trong MailHog bên ngoài để xác nhận thư chưa được gửi.
3. Tạo một yêu cầu mới với tiêu đề `HITL thử duyệt`. Bấm **Duyệt**, rồi xác nhận thư xuất hiện trong MailHog bên ngoài.

Nếu hàng đợi trống, kiểm tra agent đã đề xuất gọi công cụ gửi thư hay lượt đã kết thúc trước bước đó.

## Nhật ký và số liệu

Các lệnh dưới đây chạy từ thư mục dự án sau khi đã chuẩn bị môi trường. Hai lượt đo Utility làm mới hộp thư theo từng ca, nên dùng khi lab đang dành cho đo kiểm.

```powershell
.\.venv\Scripts\python.exe -m experiments.audit_summary
.\.venv\Scripts\python.exe -m experiments.bench_baseline --defense none
.\.venv\Scripts\python.exe -m experiments.bench_baseline --defense all
.\.venv\Scripts\python.exe -m experiments.build_matrix
```

| Dữ liệu | Ý nghĩa |
| --- | --- |
| `experiments/results_raw/logs/*.jsonl` | Sự kiện theo mã lượt chạy, gồm quyết định Guardrails, quyết định người duyệt và lỗi Ollama. |
| `matrix_asr_action.csv` | Tỷ lệ lượt có thư trong hộp thư ngoài. |
| `matrix_asr_leak.csv` | Tỷ lệ lượt có dấu vết dữ liệu nhạy cảm trong thư ngoài. |
| `utility_*.csv` | Kết quả các tác vụ hợp lệ theo cấu hình và mô hình. |

ASR hiện loại lượt lỗi hạ tầng khỏi mẫu số và giữ riêng tác động đã quan sát trong các lượt lỗi. Ô trống nghĩa là chưa có tỷ lệ. Khi đối chiếu Utility, dùng cùng nhóm model, ca kiểm thử, số lần lặp và cách chấm. CSV lịch sử có thể dùng cách tính cũ. Thư mục `experiments/results_raw/` được Git bỏ qua, nên một bản clone mới có thể chưa có số liệu.

## Xử lý lỗi thường gặp

| Hiện tượng | Cách kiểm tra |
| --- | --- |
| Không nạp được model | Chạy `ollama list` và kiểm tra đúng tên model đã chọn. |
| Ollama trả HTTP 500 | Xem thông báo theo mã lượt ở **Nhật ký kiểm toán** và nhật ký máy chủ Ollama để xác định lỗi xảy ra ở bước nào. |
| Không kết nối được MailHog | Chạy `docker compose ps` và mở thử cả hai giao diện hộp thư theo địa chỉ ở trên. |
| `.venv` báo đường dẫn Python cũ | Tạo lại môi trường ảo bằng Python đã cài trên máy hiện tại, rồi cài lại các thư viện ở bước khởi chạy. |
| Bảng kết quả trống | Kiểm tra các CSV trong `experiments/results_raw/`. Ma trận ASR cần kết quả ASR đã lưu để tổng hợp. |

## Mã nguồn và tài liệu

- `agent/` chứa vòng lặp agent và các công cụ email, SQLite.
- `guardrails/` chứa bộ lọc email, chính sách và hàng đợi duyệt.
- `lab/` chứa kết nối MailHog, dữ liệu giả và công cụ kiểm tra dấu vết.
- `experiments/` chứa script đo kiểm, nhật ký và tổng hợp số liệu. `ui/` chứa ứng dụng Streamlit.
- [Hợp đồng kỹ thuật](docs/interfaces.md) · [Mô hình đe dọa](docs/threat_model.md) · [Nhật ký Tuần 6](docs/Nhat_ky_tuan6.md) · [Khung báo cáo](docs/bao_cao_khung.md)
