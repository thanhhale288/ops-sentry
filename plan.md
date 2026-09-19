# Ops Sentry — plan

Cập nhật: 19/9/2026. Helio Devices là tenant giả. Plan này là kế hoạch sản phẩm, không phải roadmap cá nhân.

## Tiến độ (19/9/2026)

| Phạm vi | Hoàn thiện | Ghi chú |
|---|---|---|
| **Phase 0** (cây làm việc hiện tại) | **~85%** | 15/16 ô P0.1–P0.5. Thiếu `compose up` máy sạch. |
| **Cổng 13/10** (người lạ clone + compose) | **~70%** | Artifact Phase 0 chưa lên git; chưa `up --build` trên máy sạch; Gemini chưa đo live. |
| Phase 1 Eval lab | **0%** | Sau cổng. |
| Phase 2 Ca trực | **0%** | Tùy chọn, không song song Phase 1. |
| Phase 3 Một domain | **0%** | Sau tháng 9–10. |

Công thức Phase 0: năm nhóm P0.1–P0.5 trọng số đều (100 + 75 + 100 + 90 + 100) / 5. P0.2 = 75% vì 3/4 ô xong, ô `docker compose up --build` từ clone mới **chưa**. P0.4 = 90% vì năm câu stub đã khóa schema, Gemini chỉ ghi “chưa đo”.

### Phase 0 — còn thiếu (làm trước cổng)

1. **`docker compose up --build` từ clone mới** — chưa chạy. Máy này: port 8000 đang uvicorn; plugin `docker compose` không có (`docker-compose` v5 có); Colima từng down. Cần daemon Docker, cổng 8000/6333/6379/5432 trống, không `.venv`. Sau `up`, `curl POST /v1/ask` trên stack Compose (ô P0.2 còn `[ ]`).
2. **Commit artifact Phase 0** — `origin/main` chưa có: `data/denylist.json`, `docs/demo-60s/` (GIF + 4 still), `evals/SCORECARD.md`, `scripts/demo_60s.sh`, `.dockerignore`, `tests/test_ask_contract.py`. Người lạ clone remote **không** reproduce demo/scorecard/denylist v`2026-09-19.2`.
3. **Đo Gemini 5 câu** khi có `GEMINI_API_KEY` — SCORECARD đang `chưa đo — thiếu GEMINI_API_KEY`. Pytest skip test Gemini trong `tests/test_ask_contract.py`. Không fail-open sang stub.
4. **YouTube unlisted** — không bắt buộc (plan cho phép file **hoặc** link). Đã có `docs/demo-60s/demo-60s.gif`. Chỉ làm nếu cần nhúng ngoài repo.
5. **Pytest trên máy sạch** (clone trống, `pip install -r requirements.txt`) — đã xanh trên `.venv` local stub (55 passed, 1 skipped). Chưa chứng minh từ clone mới.

Không thiếu trên cây local: take 3 câu trên UI, README 60s, SCORECARD + sample 14 gold / 19 injection, injection `block_rate` 1.0, `vn-access` không overblock, denylist v`2026-09-19.2`, fallback regex khớp `Unlock all the doors`.

---

## Mục tiêu

Người lạ clone repo, chạy được agent ops nội bộ trong vài phút, và **trong 60 giây** thấy ba hành vi:

1. Câu vận hành có citation SOP (`CAM-014` flicker → SOP-CAMERA / triage, không block).
2. Câu nguy hiểm bị chặn (`Unlock all doors` → `unsafe_physical_command`).
3. Work order P1 **không tự open** — `pending_confirm`, operator bấm confirm.

Đo bằng số, không bằng slide:

| Chỉ số | Sàn cổng (13/10/2026) | Ghi chú |
|---|---|---|
| `retrieval_recall` | ≥ 0.75, mục tiêu 1.0 trên gold hiện tại | `python evals/harness.py` |
| `answer_pass_rate` | ≥ 0.75, mục tiêu 1.0 stub | Cùng harness |
| `injection_block_rate` | **1.0** | Mọi case trong `data/injection.json` |
| `n_gold` | ≥ 14 | Đã có 14 |
| `n_injection` | ≥ 12 | Đã có **19** (cây hiện tại) |
| `pytest` | xanh | `.venv/bin/python -m pytest -q` — xanh local; chưa máy sạch clone |
| Demo | Video ≤ 60s + lệnh compose/curl trong README | GIF local có; **compose up máy sạch còn thiếu**; artifact chưa commit |

Cổng **13/10/2026**: repo public, `docker compose up --build` trên máy sạch, scorecard, video 60s. Trượt cổng thì không mở nhánh mới.

## Định hướng

Một repo, một vòng: **query → denylist → (cache) → agent ≤ 4 bước → tool typed → JSON `AskResponse`**.

- Stub là đường chính (không cần API key). Gemini là nhánh phụ, **cùng schema**.
- Safety = denylist có version + eval paraphrase, không classifier cho đến khi regex hết gánh.
- Retrieval = hash dense + BM25 RRF. Không đổi encoder khi gold chưa trượt.
- Mọi `create_work_order` từ agent = `pending_confirm`.
- Không LangChain/LangGraph, không product RAG thứ hai, không ROS/robot trong repo này.

Sau cổng: **một nhánh**. Mặc định **Eval lab** (đo stub vs live, case trượt có ghi). Nhánh “ca trực” chỉ khi cần demo điều khiển ticket. Nhánh “một domain sâu” để sau.

## Đã xong (không làm lại)

- FastAPI `POST /v1/ask`, `AskResponse`, UI operator (`templates/index.html`)
- 4 tool: `search_knowledge`, `lookup_device`, `check_sla`, `create_work_order`
- Hybrid retrieve, 8 SOP, 8 devices
- Denylist `data/denylist.json` v`2026-09-19.2`, 19 injection cases
- HITL work order, audit (query đã redact), cache không nuốt pending, cache vẫn ghi audit
- Gemini native function calling; `GeminiBlocked` không fail-open sang stub
- `OPS_API_TOKEN` + `OPS_ENV=production` bắt token; UI gửi `X-Ops-Token`
- Docker Compose: API + Qdrant + Redis + Postgres
- `AGENTS.md`, `.cursor/rules/ops-sentry.mdc`, `llms.txt`

## Non-goal

- SSO/JWT gắn identity operator (ô `operator` vẫn là display name)
- Embedding host, Cohere rerank, WeKnora, LangGraph
- React SPA, Prometheus, BMS/ACS thật
- Multi-tenant, hội thoại dài, streaming SSE — trừ khi đã chọn nhánh B sau cổng

---

## Phase 0 — Cổng đóng gói (19/9 – 13/10/2026)

Mục tiêu phase: người lạ reproduce demo. Không thêm feature.

### P0.1 Video 60s  ← ưu tiên

- [x] Quay một take: Ask CAM-014 → thấy citation; Ask Unlock all doors → blocked; Ask P1 HVAC-3 → Confirm.
- [x] File hoặc unlisted link; nhúng vào README (mục “60-second demo”).
- [x] README nêu đúng 3 câu query, không copy JD.

### P0.2 Compose máy sạch

- [ ] `docker compose up --build` từ clone mới, không `.venv`.
- [x] `curl POST /v1/ask` trả JSON hợp lệ.
- [x] Ghi vào README lệnh tối thiểu (copy `.env.example`, port 8000).
- [x] Sửa lệch nếu Compose `DATABASE_URL` / token làm demo gãy.

### P0.3 Scorecard đọc được

- [x] Chạy `python evals/harness.py`, cập nhật `evals/sample-scorecard.json` cho khớp **14 gold / ≥12 injection** (hiện 19).
- [x] Thêm `evals/SCORECARD.md`: bảng chỉ số stub, lệnh reproduce, **một** case từng trượt (hoặc “không trượt — gold lexical”).
- [x] `pytest -q` xanh trên cây hiện tại (stub).

### P0.4 Stub và Gemini cùng hợp đồng

- [x] Cùng 5 câu (CAM-014, SLA ACS-11, P1 HVAC, unlock doors, jailbreak) — JSON field giống nhau.
- [x] Ghi ngắn trong SCORECARD.md nếu Gemini lệch stub (vẫn `AskResponse`).
- [x] Không đổi loop sang framework khác.

### P0.5 Tuần 4 cổng (7–13/10) — injection

- [x] Thêm paraphrase vào `data/injection.json` nếu còn lỗ; **block_rate = 1.0**.
- [x] Không overblock gold `vn-access` (“được mở hết cửa không?”).
- [x] Bump `denylist.json` version khi đổi pattern.

**Phase 0 xong khi:** video + compose + SCORECARD.md + pytest xanh + injection 1.0.

---

## Phase 1 — Eval lab (sau 13/10, mặc định)

Mục tiêu phase: harness là bằng chứng, không phải script pass.

### P1.1 Tách stub vs live

- [ ] Harness ghi `provider` vào scorecard.
- [ ] Hai artifact: `evals/scorecard-stub.json`, `evals/scorecard-gemini.json` (gemini optional, skip nếu không key).
- [ ] CI (GitHub Actions) chạy pytest + harness stub trên PR.

### P1.2 Case trượt có chủ

- [ ] `evals/failures.md`: query, expect, actual, ngày, cách bào.
- [ ] Không xóa gold để giữ 1.0 giả.

### P1.3 Red-team paraphrase

- [ ] +8–20 injection paraphrase EN/VN; denylist version mới.
- [ ] 1 test: câu vận hành thường **không** block.

### P1.4 Gold chất, không vàng số

- [ ] Chỉ thêm gold khi retrieve hoặc stub **suýt trượt**; mục tiêu ~20, không 100.
- [ ] Cấm query chỉ copy nguyên văn SOP.

**Phase 1 xong khi:** CI stub xanh; có ít nhất một lần đo Gemini hoặc ghi “chưa đo — thiếu key”; failures.md tồn tại.

---

## Phase 2 — Ca trực (tùy chọn, sau Phase 0)

Chỉ làm nếu cần demo điều khiển ticket trên lớp. Không song song Phase 1 nếu chưa có video.

### P2.1 Session ngắn

- [ ] `session_id` nhớ tối đa 5 lượt (tóm tắt audit gần nhất), không chat RAG.
- [ ] Eval: hỏi follow-up “còn SLA?” sau ACS-11 vẫn grounded.

### P2.2 Board

- [ ] UI list pending/open/cancelled không ẩn 404.
- [ ] Intern confirm; ghi `confirmed_by` (vẫn display name cho đến khi có identity).

### P2.3 SSE (nếu còn thời gian)

- [ ] Stream từng tool step; Ask đầy đủ vẫn là nguồn sự thật.

**Phase 2 xong khi:** một ca: hỏi → pending ticket → confirm trên UI, có session.

---

## Phase 3 — Một domain sâu (sau, không phải tháng 9–10)

Chọn **một**: ACS **hoặc** camera. Không thêm loại thiết bị.

- [ ] Gold adversarial trong một SOP (mâu thuẫn điều khoản, cấm export ANPR, v.v.).
- [ ] Embedding thật **chỉ khi** hash+BM25 trượt case đó.
- [ ] Adapter giả trạng thái thiết bị theo thời gian — không BMS thật.

**Phase 3 xong khi:** 8–10 case khó trong một domain, harness chỉ ra chỗ retrieval/agent sai.

---

## Thứ tự làm việc (từ 19/9)

```text
P0.1 video 60s
  → P0.2 compose máy sạch
  → P0.3 SCORECARD.md + sample-scorecard.json
  → P0.4 5 câu stub/Gemini
  → P0.5 injection tuần 4 (nếu còn lỗ)
  → [cổng 13/10]
  → Phase 1 eval lab
  → Phase 2 chỉ nếu cần demo ca trực
  → Phase 3 khi cần độ sâu SOP, không khi chán UI
```

Một việc lớn tại một thời điểm. Việc lớn tới 13/10 là **P0.1–P0.5**, không phải BM25 lần hai hay SPA.
