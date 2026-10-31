---
id: rag-eval-notes
title: RAG Evaluation Notes
type: reference
domain: ai
module: eval
tags: [eval, ragas, e-008, t-023]
priority: 2
---
# Nhận xét kết quả đánh giá RAG (T-023)

Số liệu trong `rag-eval-report.md` (sinh bởi `eval/run.py --all`) và `eval/results/<mode>.jsonl`. File này viết tay, phải cập nhật khi chạy lại eval. Lượt chạy: 2026-11-01, corpus dùng chung 2.815 point, `gpt-6-luna` trả lời và chấm, `PROMPT_VERSION` 1, `REFUSAL_THRESHOLD` 0,5, `RERANK_CANDIDATES` 5.

## Tóm tắt

| | `dense` | `hybrid` | `hybrid_rerank` (mặc định) |
|---|---|---|---|
| Faithfulness (≥ 0,80) | 0,92 | 0,90 | 0,84 |
| Hit@5 (≥ 0,75) | 0,88 | 0,90 | 0,88 |
| Từ chối đúng ngoài phạm vi (≥ 0,90) | 1,00 | 1,00 | 1,00 |
| Có trích dẫn (= 1,00) | 1,00 | 1,00 | 1,00 |
| Câu trong phạm vi được trả lời | 0,82 | **0,90** | 0,88 |
| Câu ngoài phạm vi vẫn gọi LLM | 10/10 | 10/10 | **1/10** |
| Chunk trung bình đưa cho LLM | 5,0 | 5,0 | 3,2 |
| Token vào của LLM trả lời | 78.200 | 75.193 | **44.697** |
| Độ trễ p50 / p95 (ms, trong process) | 1.612 / 2.502 | 1.507 / 2.255 | 3.587 / 5.544 |

**Cả 3 mode đều đạt 4 ngưỡng NFR-01..04.** Không câu nào trích văn bản bị thay thế. Không có lỗi và không phải thử lại.

## Nhận xét

1. **`hybrid` tốt nhất về chất lượng trên bộ này:** trả lời nhiều nhất (36/40), trúng trang nhiều nhất (0,90), faithfulness cao và nhanh nhất. `hybrid_rerank` không hơn `hybrid` ở chỉ số chất lượng nào. Với 5 ứng viên, rerank chỉ sắp xếp lại top 5 của hybrid và bỏ những chunk dưới ngưỡng, nên không kéo được chunk hạng 6–20 lên.
2. **Giá trị của rerank nằm ở việc từ chối sớm và chi phí.** 9/10 câu ngoài phạm vi bị chặn bởi ngưỡng rerank trước khi gọi LLM. Ở hai mode kia, cả 10 câu đều gọi LLM rồi được prompt từ chối. Token vào giảm khoảng 40% vì trung bình chỉ 3,2 chunk vượt ngưỡng. Đổi lại, độ trễ tăng gấp khoảng 2,4 lần (rerank trên CPU).
3. **Từ chối ngoài phạm vi đạt 100% ở cả 3 mode**, nhờ hai lớp: ngưỡng rerank và prompt bắt model trả `REFUSAL`. Câu "Phí thường niên thẻ tín dụng Vietcombank" vượt ngưỡng rerank (0,905, vì biểu phí VietinBank rất giống), nhưng LLM vẫn từ chối đúng. Vì vậy chỉ riêng ngưỡng rerank chưa đủ với câu hỏi về ngân hàng khác.
4. **Ngưỡng 0,5:** ở `hybrid_rerank` chỉ 1/40 câu trong phạm vi bị từ chối vì không có chunk nào vượt ngưỡng. Bốn câu bị từ chối còn lại là do LLM từ chối dù đã có chunk. Điểm rerank cao nhất thấp nhất trong các câu được trả lời là 0,69. Bộ này chưa cho thấy cần đổi ngưỡng.
5. **Faithfulness bị judge chấm thấp hơn thực tế.** Ở `hybrid_rerank`, cả 7 câu có điểm < 0,6 đều khớp đáp án chuẩn của golden, và mọi con số trong câu trả lời đều có trong chunk (trừ 40.000 là phép trừ hai mức phí). Phần lớn là câu về bảng phí: chunk dạng bảng markdown, câu trả lời ngắn. Vậy 0,84 là cận dưới. Nên coi faithfulness là chỉ số báo động, không phải số đo chính xác. 1 câu ở `hybrid_rerank` judge không chấm được (Nghị định 52, câu trả lời dạng danh sách dài).
6. **Câu trượt ở cả 3 mode** (ứng viên cho E-014):
   - 2 câu bảng phí bị từ chối: phí rút tiền mặt bằng thẻ tín dụng quốc tế; phí chuyển tiền ngoại tệ ra nước ngoài cho tổ chức.
   - Câu `superseded` về Điều 32c Thông tư 39 (giới hạn 100 triệu) bị từ chối.
   - Câu `cross_department` về phí chi hộ lương bị từ chối.
   - Câu Nghị định 52 về hành vi bị cấm: trả lời được nhưng không trúng trang vàng.

   Riêng `hybrid_rerank` từ chối thêm câu `cross_department` về thanh toán ngoại tệ bằng thẻ tín dụng. `dense` trượt thêm 4 câu.

## Đề xuất (owner quyết định)

- **Mode mặc định:** giữ `hybrid_rerank` nếu ưu tiên từ chối sớm và chi phí token; chuyển sang `hybrid` nếu ưu tiên tỉ lệ trả lời và độ trễ. Chênh lệch chất lượng giữa hai mode trên 50 câu là 1–2 câu, nằm trong sai số của bộ nhỏ.
- **Số ứng viên rerank:** thử `RERANK_CANDIDATES=10` trong vòng cải tiến E-014. QA của PR #64 cho thấy chunk đúng có lúc đứng hạng 6 (trên corpus khác). Cần đo lại độ trễ: 10 ứng viên trên CPU mất khoảng 5,7 giây trung vị (T-017).
- **Ngưỡng `REFUSAL_THRESHOLD`:** giữ 0,5.
- **Judge:** nếu cần số faithfulness đáng tin hơn cho bảng phí, thử judge mạnh hơn qua `JUDGE_MODEL`, hoặc bổ sung chỉ số so với `reference` (answer correctness) ở E-014.

## Giới hạn

- Bộ 50 câu nhỏ: mỗi câu là 2,5 điểm phần trăm của hit@5 và tỉ lệ trả lời.
- Model trả lời có nhiệt độ 0 nhưng không hoàn toàn cố định, nên chạy lại có thể lệch 1–2 câu.
- Độ trễ đo trong process trên máy dev 16 nhân, khi các dịch vụ compose khác cũng đang chạy. Chưa gồm HTTP, xác thực và che PII. Số này không thay cho p95 của NFR-08 (đo qua Langfuse ở E-013).
- Faithfulness bị chấm thấp hơn thực tế với bảng phí (nhận xét 5).
