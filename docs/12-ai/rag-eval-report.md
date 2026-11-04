---
id: rag-eval-report
title: RAG Evaluation Report
type: report
domain: ai
module: eval
tags: [eval, ragas, e-008, t-023]
priority: 1
---
# Báo cáo đánh giá RAG

Sinh tự động bởi `python eval/run.py`; không sửa tay (chạy lại để cập nhật). Phần nhận xét viết tay nằm ở `docs/12-ai/rag-eval-notes.md`.

## Cấu hình

- **Ngày chạy**: `2026-11-04 16:11`
- **Bộ câu hỏi**: `eval/golden.jsonl (50 câu)`
- **Model trả lời**: `alias cloud-chat qua LiteLLM; local-chat khi có chunk confidential (decide_route)`
- **Judge (faithfulness)**: `RAGAS faithfulness, cloud-chat; câu đi local chấm bằng local-chat`
- **PROMPT_VERSION**: `2`
- **k**: `5`
- **REFUSAL_THRESHOLD**: `0.5`
- **RERANK_CANDIDATES**: `8`
- **QDRANT_COLLECTION**: `bank_docs`

## Kết quả theo mode

| Chỉ số | Ngưỡng | `dense` | `hybrid` | `hybrid_rerank` |
|---|---|---|---|---|
| Faithfulness (NFR-01) | ≥ 0.8 | 0.89 ✅ | 0.82 ✅ | 0.84 ✅ |
| Hit@5 (NFR-02) | ≥ 0.75 | 0.88 ✅ | 0.90 ✅ | 0.93 ✅ |
| Từ chối đúng câu ngoài phạm vi (NFR-03) | ≥ 0.9 | 1.00 ✅ | 1.00 ✅ | 1.00 ✅ |
| Câu trả lời có trích dẫn (NFR-04)¹ | ≥ 1.0 | 1.00 ✅ | 1.00 ✅ | 1.00 ✅ |
| Câu trong phạm vi được trả lời | | 0.80 | 0.88 | 0.93 |
| Số câu được chấm faithfulness | | 32 | 35 | 37 |
| Tỉ lệ câu trả lời được chấm (faithfulness chỉ tính khi ≥ 0.9) | | 1.00 | 1.00 | 1.00 |
| Trích văn bản bị thay thế (FR-02) | = 0 | 0 ✅ | 0 ✅ | 0 ✅ |
| Lỗi khi chạy (sau khi thử lại) | = 0 | 0 ✅ | 0 ✅ | 0 ✅ |
| Số lần thử lại do dependency lỗi tạm thời | | 0 | 0 | 0 |
| Độ trễ p50 (ms) | | 1748 | 1625 | 5978 |
| Độ trễ p95 (ms) | | 12830 | 12977 | 15465 |
| Token vào (LLM trả lời) | | 88436 | 85932 | 57593 |
| Token ra (LLM trả lời) | | 2078 | 2155 | 2117 |

¹ Luôn 1,00 theo cách làm: `RagAnswerer` đổi câu trả lời không có trích dẫn hợp lệ thành câu từ chối, nên NFR-04 đạt bằng thiết kế. Câu bị đổi như vậy làm giảm dòng "Câu trong phạm vi được trả lời".

## Theo loại câu hỏi

Số câu được trả lời (`found`) và số câu retrieval trúng trang vàng (hit@5).

| Loại | Số câu | `dense` found / hit | `hybrid` found / hit | `hybrid_rerank` found / hit |
|---|---|---|---|---|
| `cross_department` | 6 | 5 / 4 | 5 / 5 | 5 / 5 |
| `fact` | 14 | 9 / 13 | 13 / 13 | 13 / 13 |
| `multi_hop` | 5 | 5 / 5 | 4 / 5 | 5 / 5 |
| `out_of_scope` | 10 | 0 / — | 0 / — | 0 / — |
| `superseded` | 4 | 4 / 4 | 4 / 4 | 4 / 4 |
| `table` | 11 | 9 / 9 | 9 / 9 | 10 / 10 |

## Câu trượt

Câu trong phạm vi bị từ chối hoặc retrieval không trúng trang vàng, và câu ngoài phạm vi vẫn được trả lời.

### `dense` (10)

- [fact, credit] Giao dịch thẻ tín dụng VietinBank phải có giá trị tối thiểu bao nhiêu thì mới được đăng ký chuyển trả góp? — từ chối
- [fact, credit] Nếu tất toán trước hạn khoản trả góp qua thẻ tín dụng VietinBank thì chủ thẻ có được hoàn phí chuyển đổi và có phải trả phí tất toán trước hạn không? — từ chối
- [fact, credit] Một chủ thẻ tín dụng cá nhân VietinBank được phát hành tối đa bao nhiêu thẻ phụ? — từ chối
- [fact, hr] Mức tham chiếu trong Luật Bảo hiểm xã hội được xác định thế nào khi mức lương cơ sở chưa bị bãi bỏ? — từ chối
- [fact, hr] Doanh nghiệp xin giấy phép cho thuê lại lao động phải ký quỹ bao nhiêu tiền? — từ chối
- [table, public] Phí rút tiền mặt bằng thẻ tín dụng quốc tế VietinBank là bao nhiêu? — từ chối
- [table, public] Phí chuyển tiền ngoại tệ đi nước ngoài cho khách hàng tổ chức tại VietinBank là bao nhiêu? — từ chối
- [cross_department, hr] Khi trả lương qua tài khoản ngân hàng, ai chịu phí liên quan, và VietinBank thu phí chi hộ lương thế nào đối với khách hàng tổ chức? — từ chối
- [cross_department, credit] Khi cho vay qua phương tiện điện tử, tổ chức tín dụng nhận biết khách hàng theo quy định nào và phải đối chiếu thông tin gì với khách hàng cá nhân? — không trúng trang
- [fact, public] Nghị định 52/2024/NĐ-CP cấm những hành vi nào liên quan đến tài khoản thanh toán và ví điện tử? — không trúng trang

### `hybrid` (6)

- [fact, credit] Nếu tất toán trước hạn khoản trả góp qua thẻ tín dụng VietinBank thì chủ thẻ có được hoàn phí chuyển đổi và có phải trả phí tất toán trước hạn không? — từ chối
- [table, public] Phí rút tiền mặt bằng thẻ tín dụng quốc tế VietinBank là bao nhiêu? — từ chối
- [table, public] Phí chuyển tiền ngoại tệ đi nước ngoài cho khách hàng tổ chức tại VietinBank là bao nhiêu? — từ chối
- [multi_hop, credit] Nếu nhận thẻ tín dụng VietinBank mà không kích hoạt thì sau bao lâu thẻ bị hủy hoặc bị khóa? — từ chối
- [cross_department, hr] Khi trả lương qua tài khoản ngân hàng, ai chịu phí liên quan, và VietinBank thu phí chi hộ lương thế nào đối với khách hàng tổ chức? — từ chối
- [fact, public] Nghị định 52/2024/NĐ-CP cấm những hành vi nào liên quan đến tài khoản thanh toán và ví điện tử? — không trúng trang

### `hybrid_rerank` (4)

- [fact, credit] Nếu tất toán trước hạn khoản trả góp qua thẻ tín dụng VietinBank thì chủ thẻ có được hoàn phí chuyển đổi và có phải trả phí tất toán trước hạn không? — từ chối
- [table, public] Phí chuyển tiền ngoại tệ đi nước ngoài cho khách hàng tổ chức tại VietinBank là bao nhiêu? — từ chối
- [cross_department, hr] Khi trả lương qua tài khoản ngân hàng, ai chịu phí liên quan, và VietinBank thu phí chi hộ lương thế nào đối với khách hàng tổ chức? — từ chối
- [fact, public] Nghị định 52/2024/NĐ-CP cấm những hành vi nào liên quan đến tài khoản thanh toán và ví điện tử? — không trúng trang

## Judge không chấm được

- Không có.
