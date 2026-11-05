---
id: rag-eval-notes
title: RAG Evaluation Notes
type: reference
domain: ai
module: eval
tags: [eval, ragas, e-008, t-023, e-014, t-038]
priority: 2
---
# Nhận xét kết quả đánh giá RAG (T-023, T-038)

Số liệu trong `rag-eval-report.md` (sinh bởi `eval/run.py --all`) và `eval/results/<mode>.jsonl`. File này viết tay, phải cập nhật khi chạy lại eval. Lượt chạy: 2026-11-01, corpus dùng chung 2.815 point, `gpt-6-luna` trả lời và chấm, `PROMPT_VERSION` 1, `REFUSAL_THRESHOLD` 0,5, `RERANK_CANDIDATES` 5. Model được nạp trước khi đo độ trễ.

## Vòng cải tiến E-014 (T-038, 2026-11-04)

`rag-eval-report.md` và `eval/results/` hiện là lượt chạy này: `bank_docs` ingest lại bằng chunker T-038 sau review vòng 1 và hai vòng review của B trên PR #105 (2.819 point, gồm nhãn classification của T-027), `PROMPT_VERSION` 2, `RERANK_CANDIDATES` 8, `gpt-6-luna` cho câu đi cloud, `qwen2.5:3b` (`local-chat`) cho câu có chunk confidential, nhánh đã merge main (T-036, T-040). Máy rảnh khi đo. Phân vị là nearest-rank như `eval/run.py` (`ordered[ceil(q·n) − 1]`); bản nháp trước của notes dùng `ordered[int(q·n) − 1]`, thấp hơn một hạng, và báo nhầm NFR-08 đạt (review T-038 F-01). Các mục từ "Tóm tắt" trở xuống là lượt T-023 (2026-11-01), giữ để so sánh.

| `hybrid_rerank` (mặc định) | Ngưỡng | T-023 | T-038 |
|---|---|---|---|
| Faithfulness (NFR-01) | ≥ 0,80 | 0,90 | 0,89 |
| Hit@5 (NFR-02) | ≥ 0,75 | 0,88 | **0,90** |
| Từ chối đúng ngoài phạm vi (NFR-03) | ≥ 0,90 | 1,00 | 1,00 |
| Có trích dẫn (NFR-04) | = 1,00 | 1,00 | 1,00 |
| Câu trong phạm vi được trả lời | | 34/40 | **35/40** |
| Câu trượt | | 7 | **6** |
| p95 trong process (eval) | | 5.028 ms | cloud 8.098, local 27.717 (n = 4) |
| p95 `/ask` trên Langfuse (NFR-08, < 10 s) | | chưa đo | **19.185 ms: chưa đạt** (cloud 8.746 đạt, local 21.899) |

`eval/run.py --all --check` đạt NFR-01..04 cả 3 mode (`dense` faithfulness 0,90 / hit@5 0,88; `hybrid` 0,83 / 0,90). Một lượt trước (code trước sửa F-16) trượt `--check` vì `hybrid` faithfulness 0,756 rồi đạt khi chạy lại cùng cấu hình: judge dao động (review F-13). Câu Điều 32c TT39 bị từ chối ở lượt này dù đã lấy đúng trang (hit) và hai văn bản đó không đổi chunk: LLM dao động, câu này cũng trượt ở T-023. NFR-08 **chưa đạt**: 3/50 trace `/ask` trên 10 s, cả ba đi `local-chat`. A (trong-hung) chấp nhận báo cáo tách theo route cho T-038 và để đường local làm follow-up (2026-11-04).

### 3 câu tệ nhất và nguyên nhân

Chọn từ lượt T-023 và kiểm lại trên trace. Ở T-023 có 5 câu trong phạm vi bị từ chối ở cả 3 mode; chọn 3 câu bảng phí vì cả ba có chung một nguyên nhân sửa được trong code (chunk bảng mất ngữ cảnh dòng). Hai câu còn lại không chọn: câu Điều 32c Thông tư 39 (`superseded`) cần đọc quan hệ giữa văn bản hợp nhất và văn bản sửa đổi, câu phí chi hộ lương (`cross_department`) cần ghép Bộ luật Lao động với biểu phí; cả hai là việc của retrieval nhiều nguồn, ngoài phạm vi chunk. Hai câu bị chấm faithfulness 0,0 cũng không chọn: câu trả lời khớp nguyên văn chunk, judge sai (xem dưới).

1. **"Phí chuyển tiền VND sang ngân hàng khác sau 15h tại quầy (khách hàng tổ chức)"**: chunk có dòng `| | B116 | - Từ 15h trở đi | 0,04% | 25.000 đ | 3.000.000 đ |` nhưng không có dòng cha "2 Chuyển tiền VND trong nước khác hệ thống". Bảng nối sang trang 2, docling đọc dòng dữ liệu đầu trang làm header, nên chunk mất cả tiêu đề cột. Model không biết 0,04% là phí của dịch vụ nào và từ chối. **Đã sửa.**
2. **"Phí rút tiền mặt bằng thẻ tín dụng quốc tế"**: dòng "3 Rút tiền mặt 4,00% 100.000 đ" ở trang 2 mất dòng nhóm "THẺ CORPORATE (Công ty)"; nhãn ô gộp bị docling lặp ở cả 6 cột làm loãng embedding. Chunk đúng đứng hạng 14 sau `hybrid`, ngoài 5 ứng viên rerank. Sau sửa chunker lên hạng 8; với 8 ứng viên reranker đưa lên top 5 và câu được trả lời (các lượt T-038 trước). **Nằm sát mép, hiện trượt lại:** sau sửa review vòng 2 của B, các chunk ở tài liệu khác xê dịch (dòng "Rút tiền mặt bằng mã QR" của thẻ ghi nợ nội địa giờ giữ đủ giá trị ở mọi cột) và chunk đúng xuống hạng 9, ngoài 8 ứng viên. A chọn giữ 8 ứng viên vì 10 ứng viên đưa p95 đường cloud sát 10 s.
3. **"Phí chuyển tiền ngoại tệ đi nước ngoài (khách hàng tổ chức)"**: chunk trang 3 đã có sẵn dòng "9 Chuyển tiền ngoại tệ khác hệ thống", "9.1 Chuyển tiền đi" và "9.1.2 B133 Chuyển tiền đi nước ngoài 0,2% 5 USD" từ trước T-038, nên đây không phải lỗi mất dòng cha (bản nháp trước của notes ghi nhầm). Nguyên nhân là xếp hạng: các chunk biểu phí thẻ quốc tế ("phí chuyển đổi ngoại tệ") giống câu hỏi hơn, chunk đúng ở hạng 13–16 sau `hybrid`. **Chưa sửa được.** 15 ứng viên rerank thì tìm được nhưng mất 11,8 s mỗi câu.

### Đã sửa

- **Chunker bảng** (`src/app/rag/chunk.py`): mỗi phần bảng lặp lại dòng nhóm (một nhãn trên mọi cột) và dòng cha đánh số gần nhất. Lặp cả chuỗi cha ("9" › "9.1") đã thử: dòng "9 Chuyển tiền ngoại tệ khác hệ thống" có mặt trên mọi phần của mục 9 và lấn mục 2 với câu "phí chuyển tiền trong nước khác hệ thống" (`tests/integration/test_ask.py` case 10); chỉ dòng cha gần nhất cho cùng hit@5 0,925 và sửa được case đó. Bảng ở đầu một trang không có text là phần tiếp theo của bảng cuối trang trước khi dòng đầu trông như dữ liệu (có chữ số, mã, hoặc ô trống) và không lặp lại tên cột của bảng đó: dòng đầu là dữ liệu, giữ dòng cha, và header cũ khi số cột còn khớp. Trang có heading hay text trước bảng, hoặc bảng có header riêng gọi tên mọi cột mà không có số, là bảng mới (review của B trên PR #105, F-01 hai vòng). Trên corpus, 13/14 bảng nối thật có dòng đầu như vậy; dòng còn lại ("Phí cấp lại PIN | | |") có ô trống. Tối đa hai dòng nhãn cột không có chữ số trước dòng đánh số đầu tiên là header. Trang mất cột STT: dòng chỉ có nhãn (số thứ tự dính trong nhãn như "3 Tra soát", hoặc nằm riêng ở cột khác) là mục mới và được lặp làm dòng cha; dòng tiêu đề không số ("Phí cấp lại PIN") chỉ đóng mục trước. Trước khi sửa, phí tra soát 100.000 đ của thẻ ghi nợ quốc tế nằm dưới "2 Phí rút tiền mặt" và `/ask` trả 100.000 đ cho câu phí rút tiền mặt ngoại mạng (review F-16); sau sửa trả đúng 9.090 đ / 3,64% tối thiểu 50.000 đ. Nhãn ô gộp chỉ giữ một lần ở dòng nhóm: một nhãn dài lặp qua các cột, đứng sau ô trống hay mã ngắn ("| | THẺ CORPORATE |…", "| B | | DỊCH VỤ SMS BANKING |…"). Dòng có nhãn riêng ("| Phát hành | Miễn phí | Miễn phí | Miễn phí |") giữ mọi giá trị, bằng nhau hay không (review của B, F-02 hai vòng).
- **`RERANK_CANDIDATES` 5 → 8** (bảng đo trong `docs/07-development/rerank.md`): hit@5 trên 50 câu 0,90 → 0,925, rerank p95 3,3 → 6,2 s. 10 ứng viên được 0,95 nhưng 7,4 s chỉ riêng rerank. int8 và cắt chunk đã thử và bỏ.
- **`cite()` từ chối câu trả lời chỉ có số đoạn** ("[3]", "[Tài liệu 1][1]"). `qwen2.5:3b` trả như vậy với vài câu confidential, và trước đây chúng được tính là có trích dẫn.
- **Prompt v2**: câu hỏi đặt trước và sau tài liệu; quy tắc 7 (đọc điều kiện, ngoại lệ), 8 (câu đầy đủ, không chỉ số đoạn), 9 (câu hỏi về sản phẩm/phí của ngân hàng khác thì từ chối). Quy tắc 9 cần vì sau khi gộp nhãn ô, chunk phí phát hành VietinBank đạt 0,57 với "Mức phí mở thẻ của Techcombank" và cả prompt v1 lẫn v2 chưa có quy tắc 9 đều trả lời bằng phí VietinBank. Với `qwen2.5:3b` trên ngữ cảnh của 40 câu (đếm bằng `cite()` mới), v1 trả lời 14/39 câu trong phạm vi và v2 16/39: ngang nhau trong độ dao động giữa các lượt. Prompt không làm qwen tốt lên rõ; các câu confidential được trả lời nhiều hơn trong eval chủ yếu nhờ chunk và rerank.

### Judge

Faithfulness từng câu dao động giữa các lần chấm: câu thẻ ghi nợ quốc tế Business ra 0,0 rồi 1,0 với cùng câu trả lời. Câu CIC ("tối đa 05 năm"), chép nguyên văn chunk, luôn 0,5 hoặc 0,0: judge tách thành mệnh đề "CIC cung cấp…", lấy chủ ngữ từ câu hỏi, rồi chấm mệnh đề đó là không có trong ngữ cảnh. Faithfulness `hybrid_rerank` qua các lượt T-038: 0,93, 0,85, 0,84, 0,89, 0,85, 0,82, 0,85, 0,89; `hybrid` có lượt 0,756 (trượt ngưỡng) rồi 0,83 ở lượt chạy lại cùng cấu hình. Điểm trung bình vẫn dùng được làm báo động; điểm từng câu không dùng để chọn câu tệ.

### NFR-08 và giới hạn của đường local

Langfuse (50 trace `/ask` thật qua HTTP, API key, tuần tự, nearest-rank, lượt cuối): p50 6,1 s, **p95 19,2 s, chưa đạt**. Đường cloud (45 câu) p95 8,7 s, đạt. Đường local (5 câu): 5,3 / 6,6 / 19,2 / 20,4 / 21,9 s; ba câu cuối là các câu trên 10 s và vì 3/50 = 6% > 5% nên kéo p95 tổng lên. Đo trực tiếp Ollama: prompt 1.400–1.700 token tốn 10–16 s chỉ để đọc (~100–140 token/s trên CPU này), câu trả lời 15–165 token thêm 1–13 s, nạp lại model sau 5 phút nhàn rỗi thêm 4,6 s. Giới hạn số token trả lời không đưa được câu local dưới 10 s nên không làm. A chọn báo cáo tách route và chấp nhận deviation; tối ưu đường local là follow-up.

### Còn lại (follow-up)

- Câu chuyển ngoại tệ ra nước ngoài và câu rút tiền mặt thẻ tín dụng (hạng 8–9 sau `hybrid`, ngay mép 8 ứng viên): cần cải thiện xếp hạng của `hybrid` cho bảng phí (ví dụ đưa tên sản phẩm vào đầu mỗi chunk bảng) thay vì tăng số ứng viên.
- **NFR-08 đường local** (deviation A chấp nhận): đưa ít chunk hơn cho `local-chat` (3 thay vì 5, giảm ~40% thời gian đọc prompt), tăng `OLLAMA_KEEP_ALIVE`; đo lại chất lượng và p95.
- Các câu vẫn trượt ở `hybrid_rerank`: tất toán trả góp trước hạn (local từ chối), phí chi hộ lương (`cross_department`), NĐ 52 không trúng trang.
- Snapshot Qdrant `qdrant-bank_docs-2026-11-01` không còn khớp chunker; cần snapshot mới sau khi merge.

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
