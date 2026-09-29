# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Báo cáo được điền từ source, output validator có trong repository và kết quả chạy/evidence đã cung cấp trong buổi làm lab. Các mục được đánh dấu **CẦN BỔ SUNG** là thông tin hoặc ảnh chưa được lưu trong `submission/evidence/`; không dùng ảnh giả hoặc tự suy đoán Trace ID.

## 1. Thông tin học viên

- **Họ và tên:** Vu Duy Diep
- **MSSV:** 2A202602703
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/VuDuyDiepAI/K4-L3A-Day13-VuDuyDiep-2A202602703-Monitoring-LLMOps
- **Commit code/evidence SHA:** `914f42cadb7985844b6d9755995ccbc2b31e918e` (commit Hoàn thành lab Day 13). Báo cáo này có một commit docs riêng ghi lại SHA.
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602703`

## 2. Evidence index

Các đường dẫn dưới đây tính từ thư mục `submission/`. Các ảnh và output liệt kê đã được lưu trong `submission/evidence/`; ảnh P95 incident riêng ở mục 12, ảnh tổng quan dashboard ở mục 11. Các mục còn chờ được ghi rõ trong checklist cuối báo cáo.

| Evidence | File / trạng thái |
|---|---|
| Baseline log validator | [`evidence/cp1-baseline-validator.txt`](evidence/cp1-baseline-validator.txt) |
| Log validator cuối CP1 | [`evidence/cp1-log-validator.txt`](evidence/cp1-log-validator.txt) |
| Log validator lần chạy mới nhất | [`evidence/02-final-log-validator.txt`](evidence/02-final-log-validator.txt) — 100/100 trên 90 record, 33 correlation ID, 0 PII leak |
| Pytest lần chạy mới nhất | [`evidence/01-pytest.txt`](evidence/01-pytest.txt) — 28 passed in 3.01 s |
| Dashboard validator | [`evidence/03-dashboard-validator.txt`](evidence/03-dashboard-validator.txt) — hợp lệ 6/6 panel |
| Structured log | [`evidence/04-structured-log.png`](evidence/04-structured-log.png) |
| PII redaction | [`evidence/05-pii-redaction.png`](evidence/05-pii-redaction.png) — terminal cho thấy email, điện thoại, CCCD và thẻ mẫu đều được che |
| Trace list, waterfall và metadata | Đã lưu: [`06-trace-list.png`](evidence/06-trace-list.png), [`07-trace-waterfall.png`](evidence/07-trace-waterfall.png), [`08-trace-metadata.png`](evidence/08-trace-metadata.png) |
| Prompt versions và rollback | Đã lưu: [`09-prompt-versions.png`](evidence/09-prompt-versions.png), [`10-prompt-promoted-v2.png`](evidence/10-prompt-promoted-v2.png), [`10-prompt-rollback.png`](evidence/10-prompt-rollback.png), [`10-production-v2-trace.png`](evidence/10-production-v2-trace.png) |
| Dashboard runtime | [`evidence/11-dashboard-overview.png`](evidence/11-dashboard-overview.png) |
| Incident metric | [`evidence/12-incident-metric.png`](evidence/12-incident-metric.png) |
| Incident log trích từ `data/logs.jsonl` | [`evidence/13-incident-log.txt`](evidence/13-incident-log.txt) |
| Incident trace | [`evidence/14-incident-trace.png`](evidence/14-incident-trace.png) |
| CP2 trace IDs baseline/candidate | [`evidence/15-cp2-trace-identifiers.txt`](evidence/15-cp2-trace-identifiers.txt) |
| Incident disable confirmation | [`evidence/16-incident-disable.txt`](evidence/16-incident-disable.txt) — `rag_slow=false` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline / điểm so sánh | Kết quả đã chạy hoặc quan sát | Evidence / ghi chú |
|---|---|---|---|
| Log validator | CP1 baseline: 30/100 trên 46 record log cũ | CP1: 100/100 trên 21 record; lần mới nhất: 100/100 trên 90 record, 33 correlation ID, 0 PII leak | [`evidence/cp1-baseline-validator.txt`](evidence/cp1-baseline-validator.txt), [`evidence/cp1-log-validator.txt`](evidence/cp1-log-validator.txt), [`evidence/02-final-log-validator.txt`](evidence/02-final-log-validator.txt) |
| Dashboard validator | Không có lần chạy baseline | Hợp lệ: 6/6 panel | [`evidence/03-dashboard-validator.txt`](evidence/03-dashboard-validator.txt) |
| Pytest | Không có lần chạy baseline | Lần mới nhất: 28 passed in 3.01 s | [`evidence/01-pytest.txt`](evidence/01-pytest.txt); chạy lại sau commit cuối |
| Trace trong project Langfuse cá nhân | — | Danh sách hiển thị ít nhất 10 trace | [`evidence/06-trace-list.png`](evidence/06-trace-list.png) |
| Prompt versioning | v1 `baseline`; v2 `candidate` | Đã chuyển `production` sang v2 rồi rollback về v1; hai trace CP2 dùng đúng v1/v2 và cùng input | Versions/rollback: ảnh 09–10; cặp trace IDs: [`evidence/15-cp2-trace-identifiers.txt`](evidence/15-cp2-trace-identifiers.txt) |
| PII leak trong log | 0 phát hiện ở baseline | 0 phát hiện ở lần cuối; validator không tìm thấy PII nguyên văn trong log | [`evidence/cp1-log-validator.txt`](evidence/cp1-log-validator.txt); scrubber mẫu che đủ bốn loại PII: [`evidence/05-pii-redaction.png`](evidence/05-pii-redaction.png) |
| CP3 latency | Ngưỡng P95: 3,000 ms | P50 2,656 ms; P95 3,813.2 ms; P99 4,043.44 ms; TTFT P95 50 ms | [`evidence/12-incident-metric.png`](evidence/12-incident-metric.png) |
| CP3 errors/retrieval | — | Error rate 0%; retrieval success 100%; 5/5 request HTTP 200 | Triệu chứng là latency, không phải lỗi retrieval |
| CP3 log/trace | — | `req-3fef08f9`: log latency 4,101 ms; trace `0d8bbea22a72cfa9`: parent 4.10 s, generation 0.16 s | Log excerpt và [`evidence/14-incident-trace.png`](evidence/14-incident-trace.png) |
## 4. Logging và PII

- **Correlation ID:** ứng dụng nhận `x-request-id` hợp lệ hoặc tạo ID theo dạng `req-<8-hex>`, bind vào ngữ cảnh request, lưu trong trace metadata và trả về response header.
- **Enrichment:** structured log có `user_id_hash`, `session_id`, `feature`, `model` và `env`.
- **Redaction:** PII được scrub trước khi JSON renderer/file writer ghi log; pattern bao gồm email, số điện thoại Việt Nam, CCCD và thẻ thanh toán.
- **Kiểm thử scrubber mẫu:** chạy `scrub_text` với email, điện thoại, CCCD và thẻ giả; output terminal đã hiện lần lượt các nhãn `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CCCD]` và `[REDACTED_CREDIT_CARD]`. Kết quả xử lý đúng; ảnh terminal xác nhận đủ bốn nhãn redaction tại [`evidence/05-pii-redaction.png`](evidence/05-pii-redaction.png).
- **Kết quả:** baseline có 20/46 record thiếu field/context và không có correlation ID; validator CP1 đạt 100/100 trên 21 record. Lần chạy mới nhất đạt 100/100 trên 90 record, có 33 correlation ID và không phát hiện PII nguyên văn. Output nằm trong Evidence index.
- **Ảnh structured log:** chụp các trường JSON đã parse từ `data/logs.jsonl`, giới hạn vào correlation ID, event, thời gian và metadata đã enrich; không đưa payload thô vào ảnh.

## 5. Tracing và prompt versioning

- **Project:** `day13-k4-l3a-2A202602703`.
- **Prompt:** `day13-chat`; trace CP3 dùng prompt managed từ Langfuse (`prompt_source=langfuse`).
- **Version/label:** v1 dùng `baseline`; v2 dùng `candidate`. Sau đó `production` được chuyển sang v2 để chạy thử và rollback về v1 theo quy trình lab.
- **Correlation ID đã thấy trong bảng Tracing:** baseline `req-c3ced892`; candidate `req-ff4f51e8`; production trên v2 `req-c602ab85`. Các giá trị này nối log với trace, không phải Trace ID.
- **Trace ID CP2 baseline:** `b8e4e80915b1c13abe58b5cb5b8ce2f4` (correlation ID `req-c3ced892`, v1/`baseline`). **Trace ID CP2 candidate:** `40e613b6703e8a8a96b9f88dfe376a0e` (correlation ID `req-ff4f51e8`, v2/`candidate`). Hai trace dùng cùng input `feature=qa`, `What is the refund policy?`; metadata được xác minh qua Langfuse Public API. Evidence: [`evidence/15-cp2-trace-identifiers.txt`](evidence/15-cp2-trace-identifiers.txt).
- **Trace CP3:** Trace ID `0d8bbea22a72cfa9`, correlation ID `req-3fef08f9`; parent `lab-agent-run` là 4.10 s và child `fake-llm-generation` là 0.16 s. Ảnh: [`evidence/14-incident-trace.png`](evidence/14-incident-trace.png).
- **Giới hạn instrumentation:** trace hiện có generation child observation nhưng chưa có retrieval child span. Vì vậy thời gian retrieval được xác định bằng so sánh parent/generation, log, và mã incident đã bật; báo cáo không gán 3.94 s chênh lệch hoàn toàn cho retrieval.
- **Rollback:** ảnh [`evidence/10-prompt-rollback.png`](evidence/10-prompt-rollback.png) xác nhận `production` đã trở lại v1. Không có request riêng sau rollback trong evidence; ảnh trạng thái label là bằng chứng rollback.

## 6. Dashboard, SLO và alerts

- Dashboard local đọc `data/logs.jsonl`, tự refresh 30 giây trong cửa sổ 60 phút và có sáu panel: latency/TTFT, traffic, errors/retrieval success, cost, tokens và quality. Cấu hình ở `config/dashboard.yaml`; cách chạy ở `docs/DASHBOARD_SETUP.md`.
- SLO: `fast_successful_requests` đạt 99.5% trong rolling 28 ngày, với request thành công trong tối đa 3,000 ms. Error budget là 0.5%, tương đương tối đa 50 request không đạt SLI trên 10,000 request.
- Alerts/runbooks: P95 > 3,000 ms trong 5 phút; error rate > 2% trong 5 phút; retrieval success < 90% trong 10 phút. Cấu hình ở `config/alert_rules.yaml`, hướng dẫn xử lý ở `docs/alerts.md`.
- Ảnh dashboard runtime cho thấy P95 vượt ngưỡng trong incident: [`evidence/11-dashboard-overview.png`](evidence/11-dashboard-overview.png).

## 7. Điều tra challenge

- **Challenge ID / cohort:** `day13-k4-l3a-monitoring-llmops-v1` / K4.
- **Incident được bật:** `rag_slow`; API xác nhận `rag_slow=True`, `tool_fail=False`, `cost_spike=False`.
- **Khoảng thời gian:** 2026-09-29 12:42:46–12:43:02 UTC (19:42:46–19:43:02 giờ Việt Nam), theo log của workload.
- **Metric:** P95 3,813.2 ms vượt ngưỡng 3,000 ms; P99 4,043.44 ms; error rate 0%; retrieval success 100%. Load test báo khoảng 15.43 giây ở phía client cho mỗi request đồng thời.
- **Log:** `req-3fef08f9`, feature `monitoring`; `response_sent` lúc `2026-09-29T12:42:51.603872Z`, `latency_ms=4101`, `ttft_ms=50`, `tool_success=true`. Trích xuất đã scrub/giới hạn field ở `evidence/13-incident-log.txt`.
- **Trace:** `0d8bbea22a72cfa9`, cùng `correlation_id=req-3fef08f9`; `lab-agent-run=4.10 s`, `fake-llm-generation=0.16 s`.
- **Root cause:** workload cố ý bật incident `rag_slow`. `app/mock_rag.py` thêm `time.sleep(2.5)` trong `retrieve()`. Retrieval chạy trước generation; generation nhanh nên LLM không phải thành phần gây chậm chính. `/chat` là async route nhưng gọi xử lý đồng bộ, khiến các request đồng thời chờ nhau; điều này giải thích thời gian client khoảng 15.4 giây so với latency xử lý từng request trong log.
- **Fix action của lab:** tắt incident `rag_slow`; API xác nhận `rag_slow=false`, `tool_fail=false`, `cost_spike=false`. Output: [`evidence/16-incident-disable.txt`](evidence/16-incident-disable.txt).
- **Preventive measure:** đưa retrieval blocking ra khỏi event loop (async I/O hoặc thread pool), đặt timeout và giới hạn thời gian retrieval, đồng thời thêm retrieval span/timing metric để lần sau nhìn trực tiếp latency của retrieval và alert theo P95 retrieval.

## 8. Giải thích và tự đánh giá

- **Quyết định kỹ thuật:** giữ nguyên starter code ngoài vùng TODO đã được giao, thêm correlation/context, PII redaction và generation tracing; điều này giảm rủi ro làm thay đổi hành vi mẫu của lab.
- **Blocker đã gặp:** lệnh inject ban đầu bị `WinError 10061` vì API không nghe ở `127.0.0.1:8000` (script dùng cố định cổng này). Khởi động Uvicorn trên đúng cổng rồi inject và load test đều trả HTTP 200.
- **Metrics → Logs → Traces:** dashboard phát hiện P95 vượt ngưỡng; correlation ID `req-3fef08f9` tìm được record log cụ thể; cùng ID tìm trace `0d8bbea22a72cfa9`; đối chiếu parent và generation cho thấy thời gian nằm ngoài LLM generation, phù hợp với retrieval bị làm chậm.
- **Prompt version, token/cost và rollback:** label giúp trace xác định phiên bản prompt đã dùng; token/cost giúp theo dõi mức sử dụng; chuyển `production` về version trước tạo đường rollback có thể kiểm chứng mà không sửa code ứng dụng.
- **Điều học được:** cần ghép metric, log và trace bằng cùng correlation ID; latency tổng cao không đồng nghĩa model generation chậm.
- **Hạn chế còn lại:** retrieval chưa có child span riêng. Các ảnh PII, Langfuse và dashboard cùng cặp CP2 trace IDs đã lưu trong Evidence index.

## 9. Checklist trước khi nộp

- [x] Báo cáo incident có metric, correlation ID/log, Trace ID, root cause và preventive measure.
- [x] Có output CP1 baseline và validator cuối; challenge config vẫn được `.gitignore`.
- [x] Đã lưu ảnh PII redaction, dashboard, Langfuse trace list/waterfall/metadata, prompt versions/rollback và incident trace.
- [x] Đã xác minh Trace ID CP2 baseline/v1 và candidate/v2 theo correlation ID; dùng cùng input (mục 5 và evidence 15).
- [x] Đã lưu xác nhận API tắt incident `rag_slow` (evidence 16).
- [x] Final local checks đã qua: pytest 28 passed, log validator 100/100 trên 90 record, dashboard validator 6/6; các output đã lưu trong evidence.
- [x] Ghi SHA commit code/evidence `914f42cadb7985844b6d9755995ccbc2b31e918e`; đã kiểm tra 20/20 đường dẫn evidence.
- [x] Đã xác nhận `.env`, `config/challenge.json` và `.vev/` đều bị Git bỏ qua; quét các file nộp không thấy pattern credentials phổ biến. Chỉ dùng PII tổng hợp trong ảnh test scrubber.
