# AI Agent Security Lab

Đồ án thử nghiệm **rủi ro prompt injection trên kiến trúc AI Agent**. Agent nhận yêu cầu, đọc email hoặc truy vấn cơ sở dữ liệu giả, rồi có thể gửi email. Bộ lab mô phỏng email nội bộ, email bên ngoài và dữ liệu nhạy cảm để quan sát hành vi của Agent khi email chứa chỉ thị độc hại.

> **Phạm vi an toàn:** Đây là môi trường học tập chạy cục bộ. MailHog chỉ hứng thư, không gửi email ra Internet; dữ liệu trong SQLite là dữ liệu giả. Không dùng dữ liệu thật hoặc đưa các cổng dịch vụ của lab ra mạng công cộng.

## Hiện trạng

- Agent, các tool, môi trường MailHog/SQLite, giao diện Streamlit và script benchmark đã có trong repo.
- Bộ dữ liệu hiện có **30 email bình thường** trong `attacks/benign/` và **5 email screening** trong `attacks/screening/`.
- Thư mục `guardrails/` hiện chưa có triển khai. Giao diện có công tắc Guardrails nhưng hiện chưa nối vào Agent; thao tác tool mặc định vẫn được cho phép. Vì vậy, không xem demo hiện tại là một hệ thống đã được bảo vệ.
- `query_db` mở SQLite ở chế độ chỉ đọc, nhưng vẫn có thể đọc các bảng/cột nhạy cảm giả. Đây là hành vi baseline để đo lường, không phải cơ chế bảo vệ dữ liệu.

## Luồng hoạt động

1. Người dùng gửi yêu cầu cho Agent.
2. Agent gọi một trong ba tool: `read_email`, `query_db` hoặc `send_email`.
3. Email được nạp vào MailHog nội bộ. Địa chỉ `@company.test` được định tuyến vào hộp thư nội bộ; địa chỉ khác được định tuyến vào hộp thư bên ngoài.
4. SQLite chứa dữ liệu công ty giả. `lab/leak_checker.py` tìm các marker dữ liệu trong hộp thư bên ngoài để đánh dấu rò rỉ.
5. Agent ghi sự kiện theo từng lần chạy vào `experiments/results_raw/logs/`.

## Cấu trúc dự án

```text
ai-agent-security/
├── agent/          # vòng lặp Agent và các tool
├── guardrails/     # vị trí dự kiến cho các lớp phòng thủ; hiện chưa triển khai
├── lab/            # MailHog, SQLite, dữ liệu giả và công cụ reset/kiểm tra
├── attacks/
│   ├── benign/     # 30 email/tình huống bình thường
│   └── screening/  # 5 email dùng để screening prompt injection
├── experiments/    # benchmark, logger, CSV và transcript đầu ra
├── ui/             # giao diện Streamlit
├── docs/           # threat model, ghi chú, hợp đồng kỹ thuật và báo cáo
├── scratch/        # các prototype ban đầu
├── config.py       # cấu hình Ollama, MailHog, SQLite và log
├── docker-compose.yml
└── README.md
```

## Yêu cầu

- Python và `pip`
- Docker Desktop với Docker Compose
- [Ollama](https://ollama.com/) và một mô hình tương thích

Repo hiện chưa có `requirements.txt`. Các lệnh dưới đây cài các thư viện Python mà UI và các script sử dụng.

## Cài đặt và khởi chạy

Chạy các lệnh từ thư mục gốc của repo, bằng PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install requests streamlit pandas
```

Khởi động hai MailHog:

```powershell
docker compose up -d
```

Tải mô hình mặc định được cấu hình trong `config.py`:

```powershell
ollama pull dolphin-llama3:8b
```

Đảm bảo Ollama đang chạy. Sau đó khởi tạo lại database và xóa nội dung hai hộp thư:

```powershell
python -m lab.reset_lab
```

Để nạp email mẫu vào hộp thư nội bộ:

```powershell
python -m lab.load_mail attacks/benign
```

Chạy giao diện:

```powershell
streamlit run ui/app.py
```

UI cho phép chat với Agent, xem log tool call và xem hộp thư nội bộ/bên ngoài. Nếu chưa có baseline CSV, tab so sánh sẽ chưa có kết quả để hiển thị.

## Chạy Agent và benchmark

Có thể chạy Agent trực tiếp sau khi đã khởi động Ollama, MailHog và nạp email:

```powershell
python -m agent.core "Read my latest email and summarize it for me."
```

Chạy baseline trên các email bình thường:

```powershell
python -m experiments.bench_baseline --models llama3.2:3b
```

Chạy screening trên các email trong `attacks/screening/`:

```powershell
python -m experiments.bench_models --only attack --models llama3.2:3b
```

Đo lại Utility khi có người duyệt Lớp 4 (mô phỏng Approve mọi yêu cầu PENDING_APPROVAL; file ra có tiền tố `utility_hitlok-`):

```powershell
python -m experiments.bench_baseline --defense all --hitl approve
```

Thống kê nhật ký kiểm toán (ALLOW / BLOCK / PENDING_APPROVAL theo lớp, quyết định của người duyệt, top lý do):

```powershell
python -m experiments.audit_summary
```

Các script benchmark tạo CSV và transcript trong `experiments/results_raw/`. Thư mục kết quả này được Git bỏ qua. Có thể thay tên mô hình bằng mô hình đã tải trong Ollama; xem thêm tùy chọn bằng `--help`.

## Kiểm tra lab

```powershell
python -m lab.selftest
```

Self-test reset lab và cố ý gửi một email chứa marker dữ liệu giả để kiểm tra bộ phát hiện rò rỉ. Sau khi chạy, reset lại nếu muốn trở về trạng thái sạch:

```powershell
python -m lab.reset_lab
```

## Kiểm thử tự động

Không cần Ollama hay MailHog: LLM và hộp thư được giả lập, cơ sở dữ liệu là `company.db` sinh trong thư mục tạm.

```powershell
python -m pip install pytest
python -m pytest
```

Bộ test gồm policy (SQL authorizer, phân tầng L2/L3/L4), chuẩn hóa tham số tool call, vòng lặp tạm dừng/chạy tiếp, hết hạn duyệt, đọc nhật ký và kết quả, và AppTest cho các trang Hàng đợi duyệt, Nhật ký kiểm toán, Bảng kết quả.

## Tài liệu

- [Threat model](docs/threat_model.md)
- [Hợp đồng kỹ thuật và cấu hình dịch vụ](docs/interfaces.md)
- [Ghi chú OWASP](docs/ghi_chu_owasp.md)
- [Khảo sát guardrails](docs/khao_sat_guardrails.md)
- [Khung báo cáo](docs/bao_cao_khung.md)
