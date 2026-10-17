Bản dịch tài liệu: LLM01:2025 Tiêm mã nhắc lệnh (Prompt Injection)

Lỗ hổng Prompt Injection xảy ra khi các câu lệnh (prompt) của người dùng làm thay đổi hành vi hoặc đầu ra của LLM theo những cách không mong muốn. Những đầu vào này có thể ảnh hưởng đến mô hình ngay cả khi con người không thể nhận biết được, do đó prompt injection không nhất thiết phải hiển thị hoặc đọc được đối với con người, miễn là nội dung đó được mô hình phân tích cú pháp (parse).

Các lỗ hổng Prompt Injection tồn tại trong cách các mô hình xử lý prompt, và cách đầu vào có thể ép mô hình chuyển dữ liệu prompt sai cách đến các phần khác của hệ thống, có khả năng khiến chúng vi phạm các nguyên tắc, tạo ra nội dung độc hại, cho phép truy cập trái phép hoặc ảnh hưởng đến các quyết định quan trọng. Mặc dù các kỹ thuật như Hệ thống tạo sinh tăng cường truy xuất (RAG) và tinh chỉnh (fine-tuning) nhằm mục đích làm cho đầu ra của LLM phù hợp và chính xác hơn, nghiên cứu cho thấy chúng không thể giảm thiểu hoàn toàn các lỗ hổng prompt injection.

Mặc dù prompt injection và bẻ khóa (jailbreaking) là các khái niệm có liên quan trong bảo mật LLM, chúng thường được sử dụng thay thế cho nhau. Prompt injection liên quan đến việc thao túng phản hồi của mô hình thông qua các đầu vào cụ thể để thay đổi hành vi của nó, bao gồm cả việc lách qua các biện pháp an toàn. Jailbreaking là một dạng của prompt injection, trong đó kẻ tấn công cung cấp các đầu vào khiến mô hình bỏ qua hoàn toàn các giao thức an toàn của nó. Các nhà phát triển có thể tích hợp các biện pháp bảo vệ vào system prompt và khâu xử lý đầu vào để giúp giảm thiểu các cuộc tấn công prompt injection, nhưng để ngăn chặn jailbreaking hiệu quả đòi hỏi phải cập nhật liên tục các cơ chế an toàn và huấn luyện của mô hình.

\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\????
Các loại lỗ hổng Prompt Injection
Prompt Injection Trực tiếp (Direct Prompt Injections)
Prompt injection trực tiếp xảy ra khi đầu vào của người dùng trực tiếp làm thay đổi hành vi của mô hình theo những cách không mong muốn hoặc không lường trước được. Đầu vào này có thể là cố ý (tức là kẻ tấn công cố tình tạo ra một prompt để khai thác mô hình) hoặc vô ý (tức là người dùng vô tình cung cấp đầu vào kích hoạt hành vi không mong muốn).

Prompt Injection Gián tiếp (Indirect Prompt Injections)
Prompt injection gián tiếp xảy ra khi một LLM chấp nhận đầu vào từ các nguồn bên ngoài, chẳng hạn như các trang web hoặc tệp tin. Nội dung từ bên ngoài có thể chứa dữ liệu mà khi mô hình diễn dịch, sẽ làm thay đổi hành vi của mô hình theo những cách ngoài ý muốn. Giống như tiêm trực tiếp, tiêm gián tiếp có thể là cố ý hoặc vô ý.

Mức độ nghiêm trọng và bản chất tác động của một cuộc tấn công prompt injection thành công có thể rất khác nhau và phụ thuộc lớn vào bối cảnh nghiệp vụ mà mô hình hoạt động, cũng như mức độ tự chủ (agency) được thiết kế cho mô hình. Tuy nhiên, nhìn chung, prompt injection có thể dẫn đến các hậu quả ngoài ý muốn, bao gồm nhưng không giới hạn ở:

Tiết lộ thông tin nhạy cảm.

Làm lộ thông tin nhạy cảm về hạ tầng hệ thống AI hoặc system prompts.

Thao túng nội dung dẫn đến kết quả đầu ra sai lệch hoặc thiên kiến.

Cấp quyền truy cập trái phép vào các chức năng (công cụ) dành cho LLM.

Thực thi các lệnh tùy ý (RCE) trong các hệ thống được kết nối.

Thao túng các quá trình ra quyết định quan trọng.

Sự trỗi dậy của AI đa phương thức (multimodal AI), có khả năng xử lý đồng thời nhiều loại dữ liệu, mang đến những rủi ro prompt injection đặc thù. Kẻ tấn công có thể khai thác sự tương tác giữa các phương thức, chẳng hạn như ẩn các chỉ thị trong một hình ảnh đi kèm với văn bản vô hại. Độ phức tạp của các hệ thống này làm mở rộng bề mặt tấn công. Các mô hình đa phương thức cũng có thể dễ bị tổn thương trước các cuộc tấn công xuyên phương thức (cross-modal) kiểu mới, vốn rất khó phát hiện và giảm thiểu bằng các kỹ thuật hiện tại. Các biện pháp phòng thủ mạnh mẽ dành riêng cho hệ thống đa phương thức là một lĩnh vực quan trọng cần được nghiên cứu và phát triển thêm.

Chiến lược Phòng ngừa và Giảm thiểu
Các lỗ hổng prompt injection luôn chực chờ do bản chất của AI tạo sinh. Với yếu tố ngẫu nhiên (stochastic) ở cốt lõi cách thức hoạt động của các mô hình, không rõ liệu có phương pháp nào phòng ngừa triệt để 100% đối với prompt injection hay không. Tuy nhiên, các biện pháp sau đây có thể giảm thiểu tác động:

Ràng buộc hành vi của mô hình: Cung cấp các chỉ thị cụ thể về vai trò, khả năng và giới hạn của mô hình trong system prompt. Buộc tuân thủ nghiêm ngặt ngữ cảnh, giới hạn phản hồi ở các tác vụ/chủ đề cụ thể và chỉ thị mô hình bỏ qua các nỗ lực sửa đổi hướng dẫn cốt lõi.

Xác định và xác thực định dạng đầu ra: Chỉ định rõ ràng định dạng đầu ra dự kiến, yêu cầu lập luận chi tiết và trích dẫn nguồn, đồng thời sử dụng mã lập trình tất định (deterministic code) để xác thực việc tuân thủ các định dạng này.

Triển khai lọc đầu vào và đầu ra: Xác định các danh mục nhạy cảm và xây dựng quy tắc để nhận diện và xử lý nội dung đó. Áp dụng các bộ lọc ngữ nghĩa và kiểm tra chuỗi để quét nội dung cấm. Đánh giá phản hồi bằng Bộ ba RAG (RAG Triad): Đánh giá mức độ liên quan của ngữ cảnh, tính có cơ sở (groundedness) và mức độ liên quan của câu hỏi/câu trả lời để nhận diện đầu ra nguy hại.

Thực thi kiểm soát đặc quyền và quyền truy cập tối thiểu: Cung cấp cho ứng dụng các token API riêng biệt cho các chức năng mở rộng và xử lý các chức năng này bằng code thay vì giao chúng cho mô hình. Hạn chế đặc quyền truy cập của mô hình ở mức tối thiểu cần thiết cho nhiệm vụ.

Yêu cầu con người phê duyệt cho các hành động rủi ro cao: Triển khai các kiểm soát có sự tham gia của con người (human-in-the-loop) đối với các hoạt động đặc quyền để ngăn chặn hành động trái phép.

Cách ly và nhận diện nội dung bên ngoài: Tách biệt và đánh dấu rõ ràng các nội dung không tin cậy để hạn chế ảnh hưởng của chúng đối với prompt của người dùng.

Thực hiện kiểm thử đối kháng và mô phỏng tấn công: Thường xuyên thực hiện kiểm thử xâm nhập và mô phỏng vi phạm, coi mô hình như một người dùng không tin cậy để kiểm tra tính hiệu quả của các ranh giới tin cậy và kiểm soát truy cập.

Các Kịch bản Tấn công Ví dụ
Kịch bản 1: Tiêm trực tiếp. Kẻ tấn công tiêm một lệnh vào chatbot hỗ trợ khách hàng, ra lệnh cho nó bỏ qua các nguyên tắc trước đó, truy vấn các kho dữ liệu riêng tư và gửi email, dẫn đến truy cập trái phép và leo thang đặc quyền.

Kịch bản 2: Tiêm gián tiếp. Người dùng dùng LLM để tóm tắt một trang web chứa các chỉ thị ẩn, khiến LLM chèn một hình ảnh liên kết đến một URL, dẫn đến việc đánh cắp (exfiltrate) cuộc trò chuyện riêng tư.

Kịch bản 3: Tiêm vô ý. Công ty đưa một lệnh ẩn vào mô tả công việc để nhận diện hồ sơ do AI viết. Một ứng viên, không biết lệnh này, dùng LLM để tối ưu CV và vô tình kích hoạt hệ thống báo động AI.

Kịch bản 4: Cố tình gây ảnh hưởng lên mô hình. Kẻ tấn công sửa đổi tài liệu trong kho lưu trữ của ứng dụng RAG. Khi truy vấn trả về nội dung bị sửa đổi, các lệnh độc hại làm thay đổi đầu ra của LLM thành kết quả sai lệch.

Kịch bản 5: Tiêm mã (Code Injection). Kẻ tấn công khai thác lỗ hổng (CVE-2024-5184) trong trợ lý email để tiêm lệnh độc hại, chiếm quyền truy cập thông tin nhạy cảm và thao túng nội dung thư.

Kịch bản 6: Chia nhỏ payload. Kẻ tấn công tải lên CV chứa các lệnh độc hại bị cắt vụn. Khi LLM đọc và kết hợp lại, các lệnh này thao túng mô hình đưa ra đánh giá tích cực bất chấp năng lực thật sự.

Kịch bản 7: Tiêm đa phương thức. Kẻ tấn công nhúng lệnh độc hại vào một bức ảnh đính kèm văn bản vô hại. Khi AI xử lý đồng thời, lệnh ẩn làm thay đổi hành vi mô hình.

Kịch bản 8: Hậu tố đối kháng. Kẻ tấn công thêm một chuỗi ký tự tưởng như vô nghĩa vào prompt, nhưng chuỗi này đủ sức thao túng đầu ra của LLM và vượt rào an toàn.

Kịch bản 9: Tấn công đa ngôn ngữ/Làm rối mã. Kẻ tấn công dùng nhiều ngôn ngữ hoặc mã hóa (như Base64, Emoji) để trốn tránh bộ lọc và điều khiển LLM.

(Danh sách liên kết tham khảo và các Framework/Taxonomy được giữ nguyên nội dung gốc).

Sự nhận định của bạn cực kỳ sắc bén. Bài viết này hoàn toàn trùng khớp với kiến trúc bảo mật trong đồ án của bạn, đóng vai trò như bản lề lý thuyết tuyệt vời:

Kịch bản 2 (Tiêm gián tiếp) phản ánh chính xác 100% tình huống Agent của bạn đọc email từ MailHog ở Tuần 4.

Chiến lược phòng thủ 4 & 5 (Quyền truy cập tối thiểu & Con người phê duyệt) chính là nền tảng học thuật cho Guardrails Lớp 2 và Lớp 4 mà bạn vừa ghi chú vào file khao_sat_guardrails.md.

Đoạn giải thích về việc "hệ thống không thể phân biệt dữ liệu và mệnh lệnh" chính là câu trả lời chuẩn xác nhất cho hiện tượng "lạm quyền tự phát" mà con mô hình dolphin-llama3 của bạn vừa gây ra ở Bài test số 1.