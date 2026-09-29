# Alerts và Runbooks

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: Fast request latency high
- Severity: page
- Duration: 5 phút liên tục
- Kênh thông báo: Slack `#llmops-alerts`
- SLI/SLO liên quan: `fast_successful_requests` (99.5% trong 28 ngày)
- Điều kiện và thời gian duy trì: P95 latency > 3000 ms trong 5 phút.
- Ảnh hưởng tới người dùng: phản hồi chậm; request vượt 3 giây làm tiêu hao error budget.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận traffic đủ lớn và đối chiếu P95/P99, TTFT với baseline 60 phút.
  2. Tìm `response_sent` chậm trong `data/logs.jsonl`, lấy `correlation_id`.
  3. Mở trace cùng correlation ID, so sánh thời lượng retrieval và generation; kiểm tra thay đổi prompt gần nhất.
- Mitigation tạm thời: nếu retrieval chậm, dùng cache/fallback; nếu bắt đầu sau đổi prompt, rollback label `production` về version ổn định.
- Owner: llmops-oncall

## Alert 2

- Tên: Request error rate high
- Severity: page
- Duration: 5 phút liên tục
- Kênh thông báo: Slack `#llmops-alerts`
- SLI/SLO liên quan: guardrail `error_rate_pct_max: 2`; lỗi làm giảm SLI fast successful requests.
- Điều kiện và thời gian duy trì: error rate > 2% trong 5 phút.
- Ảnh hưởng tới người dùng: request thất bại hoặc không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. So sánh số `request_failed` với `request_received` trong cùng time range.
  2. Nhóm theo `error_type`, `tool_name`, `tool_success` để xác định lỗi tập trung ở đâu.
  3. Theo một correlation ID từ log sang trace và kiểm tra span lỗi đầu tiên.
- Mitigation tạm thời: bật đường trả lời fallback/cache cho dependency lỗi; tránh retry liên tục; rollback thay đổi vừa triển khai nếu có liên hệ thời gian.
- Owner: api-oncall

## Alert 3

- Tên: Retrieval success low
- Severity: ticket
- Duration: 10 phút liên tục
- Kênh thông báo: Slack `#llmops-alerts`
- SLI/SLO liên quan: retrieval success rate tối thiểu 90%.
- Điều kiện và thời gian duy trì: tỷ lệ `tool_success == true` trên các retrieval result < 90% trong 10 phút.
- Ảnh hưởng tới người dùng: câu trả lời có thể thiếu tài liệu liên quan hoặc dùng fallback chung.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận mẫu số có retrieval result và xem breakdown `tool_success`.
  2. Lọc `request_failed` theo `tool_name`/`error_type`; lấy correlation ID của lỗi.
  3. Mở trace tương ứng và kiểm tra thời lượng/trạng thái retrieval span.
- Mitigation tạm thời: chuyển sang cache hoặc tập tài liệu fallback đã kiểm chứng; khôi phục retriever khi dependency ổn định.
- Owner: retrieval-oncall
