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

Số liệu trong `rag-eval-report.md` (sinh bởi `eval/run.py --all`) và `eval/results/<mode>.jsonl`. File này viết tay, phải cập nhật khi chạy lại eval. Lượt chạy: 2026-11-01, corpus dùng chung 2.815 point, `gpt-6-luna` trả lời và chấm, `PROMPT_VERSION` 1, `REFUSAL_THRESHOLD` 0,5, `RERANK_CANDIDATES` 5. Model được nạp trước khi đo độ trễ.

## Tóm tắt

| | `dense` | `hybrid` | `hybrid_rerank` (mặc định) |
|---|---|---|---|
| Faithfulness (≥ 0,80) | 0,93 | 0,91 | 0,90 |
| Hit@5 (≥ 0,75) | 0,88 | 0,90 | 0,88 |
| Từ chối đúng ngoài phạm vi (≥ 0,90) | 1,00 | 1,00 | 1,00 |
| Có trích dẫn (= 1,00, đạt bằng thiết kế¹) | 1,00 | 1,00 | 1,00 |
| Câu trong phạm vi được trả lời | 33/40 | 34/40 | 34/40 |
| Câu ngoài phạm vi vẫn gọi LLM | 10/10 | 10/10 | **1/10** |
| Chunk trung bình đưa cho LLM (câu trong phạm vi) | 5,0 | 5,0 | 3,25 |
| Token vào của LLM trả lời | 78.200 | 75.180 | **44.697** |
| Độ trễ p50 / p95 (ms, trong process) | 1.368 / 2.045 | 1.366 / 1.842 | 3.423 / 5.028 |

**Cả 3 mode đều đạt ngưỡng NFR-01..03.** NFR-04 đạt bằng thiết kế¹. Judge chấm được 100% câu trả lời ở cả 3 mode. Không câu nào trích văn bản bị thay thế. Không có lỗi và không phải thử lại.

¹ `RagAnswerer` đổi câu trả lời không có trích dẫn hợp lệ thành câu từ chối, nên tỉ lệ có trích dẫn luôn 1,00. Cái giá của quy tắc này hiện ra ở dòng "được trả lời".

## Nhận xét

1. **`hybrid` và `hybrid_rerank` ngang nhau về chất lượng trên bộ này:** cùng trả lời 34/40 câu và **trượt đúng cùng 7 câu**. `hybrid` trúng trang nhiều hơn 1 câu (0,90 so với 0,88). Với 5 ứng viên, rerank chỉ sắp xếp lại top 5 của hybrid và bỏ những chunk dưới ngưỡng, nên không kéo được chunk hạng 6–20 lên. Lượt chạy trước (cùng cấu hình) có `hybrid` trả lời 36/40 và `hybrid_rerank` 35/40: chênh lệch giữa các lượt là 1–2 câu, nên không mode nào hơn rõ rệt.
2. **Giá trị của rerank nằm ở việc từ chối sớm và chi phí.** 9/10 câu ngoài phạm vi bị chặn bởi ngưỡng rerank trước khi gọi LLM. Ở hai mode kia, cả 10 câu đều gọi LLM rồi được prompt từ chối. Token vào giảm khoảng 40% so với `hybrid`, vì trung bình chỉ 3,25 chunk vượt ngưỡng. Đổi lại, độ trễ tăng khoảng 2,5 lần (rerank trên CPU).
3. **Từ chối ngoài phạm vi đạt 100% ở cả 3 mode**, nhờ hai lớp: ngưỡng rerank và prompt bắt model trả `REFUSAL`. Câu "Phí thường niên thẻ tín dụng Vietcombank" vượt ngưỡng rerank (0,905, vì biểu phí VietinBank rất giống), nhưng LLM vẫn từ chối đúng. Vì vậy chỉ riêng ngưỡng rerank chưa đủ với câu hỏi về ngân hàng khác.
4. **Ngưỡng 0,5:** ở `hybrid_rerank`, 1 trong 6 câu trong phạm vi bị từ chối là do không có chunk nào vượt ngưỡng. 5 câu còn lại là do LLM từ chối dù đã có chunk. Điểm rerank cao nhất thấp nhất trong các câu được trả lời là 0,69. Bộ này chưa cho thấy cần đổi ngưỡng.
5. **Faithfulness bị judge chấm thấp hơn thực tế.** Ở cả 3 mode, mọi câu có điểm < 0,6 (3, 3 và 4 câu) đều khớp đáp án chuẩn của golden. Mọi con số trong các câu đó đều có trong chunk, trừ 40.000 là phép trừ hai mức phí. Phần lớn là câu về bảng phí (chunk dạng bảng markdown) hoặc câu trả lời rất ngắn. Vậy các giá trị 0,90–0,93 là cận dưới. Nên coi faithfulness là chỉ số báo động, không phải số đo chính xác.
6. **Câu trượt chung của `hybrid` và `hybrid_rerank`** (ứng viên cho E-014):
   - 3 câu bảng phí bị từ chối: phí rút tiền mặt bằng thẻ tín dụng quốc tế; phí chuyển tiền VND khác hệ thống sau 15h cho tổ chức; phí chuyển tiền ngoại tệ ra nước ngoài cho tổ chức.
   - Câu `superseded` về Điều 32c Thông tư 39 (giới hạn 100 triệu) bị từ chối.
   - 2 câu `cross_department` bị từ chối: phí chi hộ lương; thanh toán ngoại tệ bằng thẻ tín dụng.
   - Câu Nghị định 52 về hành vi bị cấm: trả lời được nhưng không trúng trang vàng.

   `dense` trượt 9 câu, gồm thêm 3 câu mà hai mode kia làm được.

## Đề xuất (owner quyết định)

- **Mode mặc định:** giữ `hybrid_rerank`. Chất lượng ngang `hybrid`, nhưng chặn được câu ngoài phạm vi trước khi tốn lượt gọi LLM và giảm khoảng 40% token. Đổi lại, độ trễ cao hơn (p95 5,0 giây trong process, vẫn dưới mức 10 giây của NFR-08). Chuyển sang `hybrid` nếu ưu tiên độ trễ.
- **Số ứng viên rerank:** thử `RERANK_CANDIDATES=10` trong vòng cải tiến E-014. QA của PR #64 cho thấy chunk đúng có lúc đứng hạng 6 (trên corpus khác). Cần đo lại độ trễ: 10 ứng viên trên CPU mất khoảng 5,7 giây trung vị (T-017).
- **Ngưỡng `REFUSAL_THRESHOLD`:** giữ 0,5.
- **Judge:** nếu cần số faithfulness đáng tin hơn cho bảng phí, thử judge mạnh hơn qua `JUDGE_MODEL`, hoặc bổ sung chỉ số so với `reference` (answer correctness) ở E-014.

## Giới hạn

- Bộ 50 câu nhỏ: mỗi câu là 2,5 điểm phần trăm của hit@5 và tỉ lệ trả lời.
- Model trả lời có nhiệt độ 0 nhưng không hoàn toàn cố định: hai lượt chạy cùng cấu hình lệch 1–2 câu mỗi mode.
- Độ trễ đo trong process trên máy dev 16 nhân, khi các dịch vụ compose khác cũng đang chạy. Chưa gồm HTTP, xác thực và che PII. Số này không thay cho p95 của NFR-08 (đo qua Langfuse ở E-013).
- Faithfulness bị chấm thấp hơn thực tế với bảng phí (nhận xét 5).
