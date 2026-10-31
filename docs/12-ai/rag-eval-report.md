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

- **Ngày chạy**: `2026-11-01 00:32`
- **Bộ câu hỏi**: `eval/golden.jsonl (50 câu)`
- **Model trả lời**: `alias cloud-chat qua LiteLLM`
- **Judge (faithfulness)**: `RAGAS faithfulness, cloud-chat`
- **PROMPT_VERSION**: `1`
- **k**: `5`
- **REFUSAL_THRESHOLD**: `0.5`
- **RERANK_CANDIDATES**: `5`
- **QDRANT_COLLECTION**: `bank_docs`

## Kết quả theo mode

| Chỉ số | Ngưỡng | `dense` | `hybrid` | `hybrid_rerank` |
|---|---|---|---|---|
| Faithfulness (NFR-01) | ≥ 0.8 | 0.93 ✅ | 0.91 ✅ | 0.90 ✅ |
| Hit@5 (NFR-02) | ≥ 0.75 | 0.88 ✅ | 0.90 ✅ | 0.88 ✅ |
| Từ chối đúng câu ngoài phạm vi (NFR-03) | ≥ 0.9 | 1.00 ✅ | 1.00 ✅ | 1.00 ✅ |
| Câu trả lời có trích dẫn (NFR-04)¹ | ≥ 1.0 | 1.00 ✅ | 1.00 ✅ | 1.00 ✅ |
| Câu trong phạm vi được trả lời | | 0.82 | 0.85 | 0.85 |
| Số câu được chấm faithfulness | | 33 | 34 | 34 |
| Tỉ lệ câu trả lời được chấm (faithfulness chỉ tính khi ≥ 0.9) | | 1.00 | 1.00 | 1.00 |
| Trích văn bản bị thay thế (phải 0) | | 0 | 0 | 0 |
| Lỗi khi chạy (sau khi thử lại) | | 0 | 0 | 0 |
| Số lần thử lại do dependency lỗi tạm thời | | 0 | 0 | 0 |
| Độ trễ p50 (ms) | | 1368 | 1366 | 3423 |
| Độ trễ p95 (ms) | | 2045 | 1842 | 5028 |
| Token vào (LLM trả lời) | | 78200 | 75180 | 44697 |
| Token ra (LLM trả lời) | | 1939 | 1958 | 1845 |

¹ Luôn 1,00 theo cách làm: `RagAnswerer` đổi câu trả lời không có trích dẫn hợp lệ thành câu từ chối, nên NFR-04 đạt bằng thiết kế. Câu bị đổi như vậy làm giảm dòng "Câu trong phạm vi được trả lời".

## Theo loại câu hỏi

Số câu được trả lời (`found`) và số câu retrieval trúng trang vàng (hit@5).

| Loại | Số câu | `dense` found / hit | `hybrid` found / hit | `hybrid_rerank` found / hit |
|---|---|---|---|---|
| `cross_department` | 6 | 5 / 4 | 4 / 5 | 4 / 4 |
| `fact` | 14 | 13 / 13 | 14 / 13 | 14 / 13 |
| `multi_hop` | 5 | 4 / 5 | 5 / 5 | 5 / 5 |
| `out_of_scope` | 10 | 0 / — | 0 / — | 0 / — |
| `superseded` | 4 | 3 / 4 | 3 / 4 | 3 / 4 |
| `table` | 11 | 8 / 9 | 8 / 9 | 8 / 9 |

## Câu trượt

Câu trong phạm vi bị từ chối hoặc retrieval không trúng trang vàng, và câu ngoài phạm vi vẫn được trả lời.

### `dense` (9)

- [fact, hr] Doanh nghiệp xin giấy phép cho thuê lại lao động phải ký quỹ bao nhiêu tiền? — từ chối
- [table, public] Phí rút tiền mặt bằng thẻ tín dụng quốc tế VietinBank là bao nhiêu? — từ chối
- [table, public] Khách hàng tổ chức chuyển tiền VND sang ngân hàng khác sau 15h tại quầy thì bị thu phí bao nhiêu? — từ chối
- [table, public] Phí chuyển tiền ngoại tệ đi nước ngoài cho khách hàng tổ chức tại VietinBank là bao nhiêu? — từ chối
- [multi_hop, public] Phí đóng thẻ ghi nợ quốc tế Business và thẻ ghi nợ nội địa Business của VietinBank chênh nhau bao nhiêu? — từ chối
- [superseded, credit] Giới hạn dư nợ 100 triệu đồng khi tổ chức tín dụng cho cá nhân vay phục vụ đời sống bằng phương tiện điện tử (Điều 32c Thông tư 39) có còn áp dụng không? — từ chối
- [cross_department, hr] Khi trả lương qua tài khoản ngân hàng, ai chịu phí liên quan, và VietinBank thu phí chi hộ lương thế nào đối với khách hàng tổ chức? — từ chối
- [cross_department, credit] Khi cho vay qua phương tiện điện tử, tổ chức tín dụng nhận biết khách hàng theo quy định nào và phải đối chiếu thông tin gì với khách hàng cá nhân? — không trúng trang
- [fact, public] Nghị định 52/2024/NĐ-CP cấm những hành vi nào liên quan đến tài khoản thanh toán và ví điện tử? — không trúng trang

### `hybrid` (7)

- [table, public] Phí rút tiền mặt bằng thẻ tín dụng quốc tế VietinBank là bao nhiêu? — từ chối
- [table, public] Khách hàng tổ chức chuyển tiền VND sang ngân hàng khác sau 15h tại quầy thì bị thu phí bao nhiêu? — từ chối
- [table, public] Phí chuyển tiền ngoại tệ đi nước ngoài cho khách hàng tổ chức tại VietinBank là bao nhiêu? — từ chối
- [superseded, credit] Giới hạn dư nợ 100 triệu đồng khi tổ chức tín dụng cho cá nhân vay phục vụ đời sống bằng phương tiện điện tử (Điều 32c Thông tư 39) có còn áp dụng không? — từ chối
- [cross_department, hr] Khi trả lương qua tài khoản ngân hàng, ai chịu phí liên quan, và VietinBank thu phí chi hộ lương thế nào đối với khách hàng tổ chức? — từ chối
- [cross_department, credit] Chủ thẻ tín dụng VietinBank thanh toán bằng ngoại tệ ở nước ngoài thì giao dịch được ghi nhận thế nào và chịu những phí gì? — từ chối
- [fact, public] Nghị định 52/2024/NĐ-CP cấm những hành vi nào liên quan đến tài khoản thanh toán và ví điện tử? — không trúng trang

### `hybrid_rerank` (7)

- [table, public] Phí rút tiền mặt bằng thẻ tín dụng quốc tế VietinBank là bao nhiêu? — từ chối
- [table, public] Khách hàng tổ chức chuyển tiền VND sang ngân hàng khác sau 15h tại quầy thì bị thu phí bao nhiêu? — từ chối
- [table, public] Phí chuyển tiền ngoại tệ đi nước ngoài cho khách hàng tổ chức tại VietinBank là bao nhiêu? — từ chối
- [superseded, credit] Giới hạn dư nợ 100 triệu đồng khi tổ chức tín dụng cho cá nhân vay phục vụ đời sống bằng phương tiện điện tử (Điều 32c Thông tư 39) có còn áp dụng không? — từ chối
- [cross_department, hr] Khi trả lương qua tài khoản ngân hàng, ai chịu phí liên quan, và VietinBank thu phí chi hộ lương thế nào đối với khách hàng tổ chức? — từ chối
- [cross_department, credit] Chủ thẻ tín dụng VietinBank thanh toán bằng ngoại tệ ở nước ngoài thì giao dịch được ghi nhận thế nào và chịu những phí gì? — từ chối
- [fact, public] Nghị định 52/2024/NĐ-CP cấm những hành vi nào liên quan đến tài khoản thanh toán và ví điện tử? — không trúng trang

## Judge không chấm được

- Không có.
