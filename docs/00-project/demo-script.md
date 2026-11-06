---
id: five-minute-demo-script
title: Five-minute banking assistant demonstration
type: reference
domain: project
module: ui
tags: [demo, ui, t-043, t-042]
priority: 2
---
# Five-minute demonstration

## Goal and verification modes

Show the FR-12 UI flow: trusted roles, cited answers, department boundaries,
sensitive routing, a loan tool and a ticket that writes only after a different
authenticated approver decides. The audience sees Vietnamese questions/UI labels;
these instructions explain them in English.

| Mode | What it demonstrates | Evidence limit |
|---|---|---|
| Default fake startup | Real Compose API/worker/Redis wiring and seeded read-only tools | Canned answers; fake LLM does not select tools or establish document quality |
| Controlled UI rehearsal | The timed interaction sequence through Streamlit AppTest, real FastAPI/API-key auth, graph/masking and SQLite, with controlled retrieval/model outputs | No live provider, real-corpus retrieval, browser-layout or latency claim |
| Live presentation | UI against the configured real RAG corpus and cloud/local gateway | Must pass the real preflight below; model outputs can vary |

Run the [README](../../README.md) fake startup first. The clock below begins
**after preflight**. First image builds, package/model downloads, corpus restore,
key provisioning and model warm-up do not fit inside five minutes.

## Preflight before the audience arrives

1. Complete README startup, explicit synthetic seeding and UI key provisioning.
   Use `synthetic-user-1` (credit staff), `synthetic-user-2` (HR staff) and distinct
   `demo-approver` (credit approver). Keep generated keys in private `.env.local`;
   do not put credentials in slides, screenshots or source. `AUTH_BACKEND=apikey`
   is required: fake auth maps every role to `dev` and cannot prove approvals/RBAC.
2. For live presentation set `RAG_BACKEND=real`, `LLM_BACKEND=litellm` and the
   private provider key. `make setup` installs the full host tools needed for
   snapshot restore; `gh` is required by the download command below. Start
   `make up PROFILE=local-llm` and explicitly pull `qwen2.5:3b` as in README.
3. On a **fresh Qdrant with no bank_docs collection**, restore the approved snapshot:

   ```bash
   mkdir -p output/demo-snapshot
   gh release download qdrant-bank_docs-2026-11-05-2819 \
     --repo T1xNTH/bank-assistant --dir output/demo-snapshot
   (cd output/demo-snapshot && \
     echo 'e03749c9f0487f153013a577f15b026e29b6710ee3f819d279003a8f3a4fa4d3  bank_docs-2819-2026-11-05.snapshot' \
     | sha256sum --check -)
   make restore BACKUP_DIR=output/demo-snapshot
   ```

   Restore checks the manifest/count and refuses an existing collection. Do not
   delete a shared collection to rerun this step. Reuse an existing corpus only
   when its approved origin/configuration is known, or use a separate fresh Compose
   project with the published ports free. Reconstructed PDF page breaks may differ;
   the expected pages below refer to the pinned 2819-point snapshot.
4. Run `make smoke` and verify both aliases with the synthetic gateway smoke:

   ```bash
   docker compose -f infrastructure/compose.yaml --env-file .env.local exec -T litellm \
     python - < scripts/smoke_llm.py
   ```

   Gateway health alone does not prove inference. Do not begin if local inference
   is unavailable; sensitive requests must not fall back to the cloud.
5. Start `make ui`, open `http://127.0.0.1:8501`, confirm all three sidebar roles,
   ask the Keypass question once and wait for the response to warm the actual API
   process. First real retrieval loads bge-m3/reranker weights. Keep the local model
   warm; make a fresh UI session for the timed sequence if needed.

Optional Langfuse needs separate `obs` setup and keys. If absent, show response
route/latency only; neither one request nor fake timing is an NFR-08 p95 measurement.

## Timed presentation

| Time | Action in UI | Expected observation |
|---|---|---|
| 0:00–0:45 | Choose **Nhân viên tín dụng (credit, staff)**. In **Hỏi đáp tài liệu**, ask **Phí cung ứng thiết bị xác thực Keypass cho khách hàng tổ chức dùng eFAST là bao nhiêu?** | Answer states 330.000 VND/device before VAT, citation `dichvunhdt.pdf` page 7, and route. This is a public question eligible for cloud; actual route can be affected by retrieved classification. |
| 0:45–1:30 | Still credit, ask **Mức lương tối thiểu tháng vùng I là bao nhiêu?** Then switch to **Nhân viên nhân sự (hr, staff)** and ask the same question. | Credit must not receive the HR-only source. A refusal or answer grounded only in allowed public sources is acceptable. HR should cite `293-cp.signed.pdf` page 2 and 5.310.000 VND for the pinned corpus. Sidebar selection changes the actual API key; labels alone do not grant access. |
| 1:30–2:15 | Return to credit. Ask **Liên hệ 0912345678. Phí cung ứng thiết bị xác thực Keypass là bao nhiêu?** | Route is **local** because the input contains a synthetic phone number. Generated output/model inputs must not expose that raw phone number. The local UI retains what the operator typed in its own history; do not claim that input panel is anonymized. |
| 2:15–3:00 | Open **Agent và duyệt**, start a new conversation and send **Vay 100 triệu, lãi 12%/năm, 12 tháng trả góp đều thì mỗi tháng trả bao nhiêu?** | Tool-rendered schedule: first payment 8.884.878,87 VND and total interest 6.618.546,40 VND, no fees/day-count conventions. Monetary values are rendered by code, not a second model call. |
| 3:00–4:15 | In the same agent thread send **Tạo ticket kiểm tra phí, liên hệ 0912345678**. Inspect the pending action, then switch to **Người duyệt (approver)** and click **Duyệt**. | Pending `tao_ticket` has masked summary; no ticket is written before approval. A different authenticated approver resumes it. The UI retains completed status and the returned ticket ID after rerun. |
| 4:15–5:00 | Use **Duyệt theo thread id (thread từ phiên khác)** to repeat the same decision. Then return to credit's document tab and ask **Câu hỏi ngoài phạm vi**. | Repeated decision returns HTTP 409 without another ticket. Out-of-scope question is safely refused when unsupported; no fabricated source. Finish by showing the saved quality/latency table, explicitly labelled as earlier evidence. |

If time allows after the clock: in a staff agent thread ask **Cho xem 5 giao dịch
gần nhất**. The seeded user can see only its five transactions, with account
references and masked text. This optional step requires a functioning tool-selecting
model; it is not supplied by the generic runtime fake LLM.

## Stop conditions and honest fallback

- A 401/403 means key/role setup needs correction; do not change authorization to
  fake to demonstrate two-person approval. Missing role means its UI key is blank.
- A 503, missing collection, unavailable local model or incorrect corpus stops
  the live presentation. Check `make logs PROFILE=local-llm` privately and preflight
  again; do not substitute a model call with saved output while labelling it live.
- No cited answer can happen with a model/retrieval miss. Show the refusal and
  distinguish it from the saved full-golden quality figures; keep the threshold.
- An agent clarification is not a completed calculation or approved ticket.
  Supply the missing details or show the controlled rehearsal with its scope stated.
- Ticket/checkpoint/audit commits are separate: after a decision 503, reconcile
  the existing ticket before retrying. Never create a replacement blindly.

## Controlled rehearsal and evidence capture

With development dependencies installed, execute:

```bash
python -m pytest tests/unit/test_demo_script.py tests/unit/test_ui.py -q
```

The new rehearsal follows the same ordered role/question/PII/loan/approval/replay
steps with a scripted model and controlled hits. It uses real API-key validation,
RAG answer/citation/routing code, agent graph, masking, SQLite and Streamlit state.
It checks the ticket count before and after approval and rejects replay. Existing
UI cases add external-thread approve/reject and visible-result persistence.
This is automated UI-flow evidence, not a claim that a human watched a browser or
that a live provider/corpus run completed. Record live runs separately with commit,
snapshot/model settings, results/failures and sanitized screenshots/logs.

After the demo stop the UI with Ctrl+C and run `make down PROFILE=local-llm`.
Preserve data volumes and evidence; no reset or release/tag is part of this script.
