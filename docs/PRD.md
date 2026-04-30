# PRD: CSRD-Lake

> **Status:** Draft — awaiting approval
> **Author:** Pyae Sone (Seon)
> **Date:** 2026-04-30
> **Last Updated:** 2026-04-30
> **Intended Scope:** PORTFOLIO PIECE (per /moat-check 2026-04-30; refuse moat claims in any pitch copy)

---

## 0. Context (read first)

This project went through `/brainstorm → /moat-check → /prfaq` before scaffolding. The verdict, decisions, and killed claims live alongside this PRD:

- `C:/Users/pyaes/claude-workspace/career-ops/applications/2026-04-30-freelance-cloud-data-engineer/BRAINSTORM.md`
- `.../MOAT-CHECK.md` — verdict: **YELLOW (GREEN as portfolio with required pivot)**
- `.../PRFAQ.md` — verdict: **3.6/5 REFINE IT** (validation gap acknowledged, build greenlit)

**Killed claims (NEVER use in any artifact, README, README screenshot, Loom, or recruiter pitch):**

- ❌ "Replaces a €40-80k/year MSCI/Sustainalytics subscription" — demonstrably wrong (MSCI sells curated ratings + 11K-issuer coverage at $200K-$2M, not PDF parsing; Briink ships exact PDF→ESRS at €195/month)
- ❌ Any "vendor displacement" framing
- ❌ Any inflated metric (PDF count, ESRS metric count, accuracy %) not earned by hand-verification

**Approved framing:**

- ✅ "Reference implementation of the Capgemini Sustainability Data Hub / PwC ESG Reporting Manager pattern, built solo in 30 hours"
- ✅ "End-to-end CSRD/ESRS data pipeline with multilingual GenAI extraction, source citation, and audit lineage"
- ✅ Engineering metrics with explicit test conditions

---

## 1. Problem Statement

### What problem are we solving?

Pyae Sone Kyaw is positioning as a freelance **Cloud Data Engineer + Data Science + AI** hybrid for the Paris consulting and French G-SIB market (TJM €650/day starting ask). His existing portfolio is strong on Azure data pipelines (Floware), GenAI/RAG (Siloett), and event-driven Java back-ends (mobility-pulse, cdr-pipeline) — but it lacks **a single, lakehouse-shaped, modern-data-stack-native portfolio piece** that a Big-4 partner can recognize in 5 seconds as "this person ships at bank-grade depth."

### Who has this problem?

- **Primary user (project consumer):** The Paris recruitment agency partner forwarding Pyae's CV to Big-4 / French G-SIB CSRD programs. They need a 90-second proof point to attach to the candidate brief.
- **Secondary user (decision-maker):** The Big-4 staffing technical lead or French bank Head of Sustainable Finance who screens the GitHub repo for 5 minutes and decides whether to book a 30-minute technical screen.
- **Builder:** Pyae himself, with a hard 30-hour budget across two weekends.

### Why now?

- French G-SIBs (BNP Paribas, Société Générale, Crédit Agricole, BPCE) face CSRD wave-1 reporting in 2026; sustainable-finance data teams are actively hiring contractors fluent in Snowflake/dbt/Airflow + GenAI extraction.
- Capgemini, Deloitte, and PwC are publicly shipping "Sustainability Data Hub" / "ESG Reporting Manager" platforms to French banks today — a portfolio piece reverse-engineering this pattern is timely.
- Pyae's recruiter conversation is open NOW; CV+portfolio packet target send date is **~14 days from now**.

---

## 2. Success Criteria

### Primary metric

**A Big-4 staffing technical lead spends <5 minutes on the CSRD-Lake GitHub repo and books a 30-minute technical screen with Pyae.**

This is binary, observable, attributable to the project. Measured by: number of recruiter-forwarded candidates → screens booked, with CSRD-Lake link in the brief.

### Secondary metrics (engineering-defensible)

- [ ] ≥30 corporate sustainability PDFs ingested (CAC 40 mandatory; DAX 40 stretch)
- [ ] ≥2,000 ESRS metric values extracted and landed in `fact_disclosure`
- [ ] ≥95% extraction accuracy on a hand-verified gold set of ≥800 datapoints (1,600 stretch)
- [ ] FR + EN multilingual coverage with documented per-language accuracy
- [ ] dbt tests: 100% pass rate on uniqueness, not_null, accepted_values, and ≥3 custom tests
- [ ] End-to-end pipeline runs cold-start in <15 minutes (Snowflake free trial + Docker Airflow + Claude API)
- [ ] README has explicit test conditions for every claim
- [ ] Source citation per extracted metric (page number + extraction snippet)

### What does "done" look like?

- Public GitHub repo at `github.com/soneeee22000/csrd-lake` (MIT license)
- Live Snowflake account with populated star schema; recruiter can see screenshots
- Next.js dashboard deployed (Vercel) showing per-company ESG profile + synthetic loan-book rollup
- dbt docs site deployed (Netlify or GitHub Pages) showing lineage + model documentation
- README with 4 sections: Hero metrics, Architecture, Reproducibility, Portability
- 90-second Loom walkthrough linked from README
- All quality gates from §10 passed

---

## 3. User Stories & Acceptance Criteria

### Story 1 — Recruiter forwards a working portfolio link

**As a** Paris recruitment agency partner, **I want to** attach a single GitHub URL + Loom link to a candidate brief, **so that** the Big-4 staffing lead has the proof they need in their inbox.

**Acceptance Criteria:**

- [ ] Given the README is opened, when reader scrolls 1 screen, then they see hero metrics (PDFs ingested, ESRS metrics extracted, accuracy on gold set, languages covered) above the fold
- [ ] Given a reader clicks the Loom link, when the video starts, then within 30 seconds they see the live Snowflake schema + dbt lineage + sample LLM extraction
- [ ] Given a reader inspects any hero metric, when they look for test conditions, then a "Methodology + Test Conditions" section explains exactly how the metric was earned

### Story 2 — Big-4 technical lead inspects the architecture

**As a** Big-4 staffing technical lead, **I want to** verify CSRD-Lake implements the same architectural pattern as Capgemini Sustainability Data Hub / PwC ESG Reporting Manager, **so that** I can pitch Pyae as a contractor who fits our existing delivery teams.

**Acceptance Criteria:**

- [ ] Given the repo is open, when reader looks at the architecture diagram, then they see ingest → extract → land → transform → expose layers explicitly named
- [ ] Given they inspect the dbt project, when they open the lineage graph, then dimension and fact tables are visibly modeled with documented joins
- [ ] Given they read `docs/PORTABILITY.md`, when they look for stack-mapping, then Snowflake → Synapse, Airflow → ADF, Claude → Azure OpenAI mappings are explicit with rationale
- [ ] Error state: if any architectural layer is mocked or stubbed, README must label it as such — no false claims of completeness

### Story 3 — Pyae demonstrates the pipeline end-to-end in 5 minutes

**As** Pyae **in a 30-minute technical screen**, **I want to** demonstrate cold-start ingestion → extraction → Snowflake population → dashboard refresh in under 5 minutes, **so that** the screening converts to a contract offer.

**Acceptance Criteria:**

- [ ] Given a fresh clone, when `make demo` is run, then within 15 minutes the full pipeline runs and the dashboard shows fresh data
- [ ] Given `make demo` fails, when error is shown, then it points to the specific missing env var or service
- [ ] Given the demo is mid-execution, when an LLM call returns malformed output, then the pipeline retries with backoff + flags the metric as "extraction_failed"

### Story 4 — Confidence-scored extraction routes to human review

**As a** data engineer reviewing extraction quality, **I want** every extracted metric to carry a confidence score and a source citation, **so that** I can audit-trail back to the source PDF and route low-confidence values to human review.

**Acceptance Criteria:**

- [ ] Given any ESRS metric is extracted, when stored in `fact_disclosure`, then `confidence_score` (0.0-1.0) and `source_citation` (page + snippet) columns are populated
- [ ] Given confidence_score < 0.80, when the dbt model `mart_disclosure_clean` runs, then those rows route to `mart_disclosure_review_queue` instead of `mart_disclosure_published`
- [ ] Given a metric is in the review queue, when human verifies + approves, then the value is promoted to `mart_disclosure_published` with an audit log entry

### Story 5 — README defends every claim it makes

**As a** Big-4 partner skeptical of portfolio metrics, **I want** every quantitative claim in the README to have explicit test conditions, **so that** I trust the engineering before booking the technical screen.

**Acceptance Criteria:**

- [ ] Given a "X% accuracy" claim, when reader scans for test conditions, then the gold-set size, language distribution, metric distribution, and verification method are stated
- [ ] Given a "N PDFs" claim, when reader scans, then the source list (CAC 40 / DAX 40), date range, and any exclusions are stated
- [ ] Given a "<15 min cold-start" claim, when reader scans, then the hardware, network assumptions, and excluded steps (e.g., LLM API rate limits) are stated

---

## 4. Technical Architecture

### Stack Decision

| Layer                   | Choice                                                                                                  | Why                                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Ingestion orchestration | **Apache Airflow 2.10** (Docker Compose local)                                                          | Modern data stack canonical; portable to Astronomer / MWAA / ADF                                      |
| PDF source              | **CAC 40** (mandatory v1) + **DAX 40** (stretch) corporate IR pages + ESMA registry                     | Public, defensible, multilingual coverage of FR + EN                                                  |
| Extraction              | **Claude Sonnet (Anthropic API)** primary + **Mistral Large** fallback, structured outputs via Pydantic | User has hands-on with both; Claude's structured output is most reliable; Mistral as cost/FR fallback |
| Schema                  | **Pydantic v2** for ESRS metric definitions                                                             | Type-safe, validates structured LLM outputs at the boundary                                           |
| Warehouse               | **Snowflake free trial** (30-day, $400 credits)                                                         | Real recruiter-visible cloud account; star schema demo                                                |
| Transformation          | **dbt-core 1.9** with `dbt-snowflake` adapter                                                           | Modern data stack canonical; lineage + tests + docs out of the box                                    |
| Dashboard               | **Next.js 16 + Vercel**                                                                                 | Pyae's strength; matches existing portfolio aesthetic; deployable in 6-8h                             |
| Confidence scoring      | Per-metric LLM logprobs + structural validation rule set                                                | Routes <0.80 to human review queue                                                                    |
| Hosting                 | **GitHub** (repo) + **Vercel** (dashboard) + **Netlify or GitHub Pages** (dbt docs)                     | Free, public, recruiter-visible                                                                       |
| CI                      | **GitHub Actions**: ruff + mypy + pytest + dbt build                                                    | Quality gates enforced pre-merge                                                                      |

### Architecture Diagram

```mermaid
graph TD
    A[CAC 40 / DAX 40 IR pages] -->|HTTP scrape| B[Airflow: ingest_pdfs DAG]
    B -->|raw PDFs| C[(local /data/raw/)]
    C -->|airflow task| D[extract_esrs DAG]
    D -->|PDF chunks| E[Claude Sonnet API + Pydantic schemas]
    E -->|metric + confidence + citation| F[(local staging tables)]
    F -->|airflow load task| G[(Snowflake: raw.disclosure_extracted)]
    G -->|dbt seed/run| H[(Snowflake: staging.stg_disclosure)]
    H -->|dbt model| I[(Snowflake: marts.fact_disclosure + dim_company + dim_metric + dim_period)]
    I -->|conditional split| J[(marts.mart_disclosure_review_queue)<br/>confidence < 0.80]
    I -->|conditional split| K[(marts.mart_disclosure_published)<br/>confidence >= 0.80]
    K -->|REST/Snowflake SQL API| L[Next.js dashboard on Vercel]
    H -->|dbt docs generate| M[dbt lineage + docs site]
```

### Data Model — Star Schema

| Table                          | Type      | Key columns                                                                                                                                                                                               |
| ------------------------------ | --------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dim_company`                  | Dimension | company_id (PK), name, ticker, country, sector, employees, revenue_eur                                                                                                                                    |
| `dim_metric`                   | Dimension | metric_id (PK), esrs_topic, esrs_disclosure, metric_name, unit, data_type, mandatory_flag                                                                                                                 |
| `dim_period`                   | Dimension | period_id (PK), fiscal_year, period_start, period_end, reporting_basis                                                                                                                                    |
| `fact_disclosure`              | Fact      | disclosure_id (PK), company_id (FK), metric_id (FK), period_id (FK), value_numeric, value_text, confidence_score, source_pdf_url, source_page, source_snippet, language, model_used, extraction_timestamp |
| `mart_disclosure_published`    | Mart      | confidence_score >= 0.80 AND human_approved IS NULL OR human_approved = TRUE                                                                                                                              |
| `mart_disclosure_review_queue` | Mart      | confidence_score < 0.80 OR human_approved = FALSE                                                                                                                                                         |

### Key API / Pipeline Endpoints

| Component         | Endpoint / DAG                         | Purpose                                                                           |
| ----------------- | -------------------------------------- | --------------------------------------------------------------------------------- |
| Airflow DAG       | `ingest_pdfs`                          | Daily schedule (manual trigger v1); discovers + downloads new sustainability PDFs |
| Airflow DAG       | `extract_esrs`                         | Triggered by ingest; reads PDFs, calls LLM, writes to staging                     |
| Airflow DAG       | `load_to_snowflake`                    | Triggered by extract; bulk-loads staging to `raw.disclosure_extracted`            |
| dbt model         | `staging.stg_disclosure`               | Cleans + types raw extractions                                                    |
| dbt model         | `marts.fact_disclosure`                | Final fact table with confidence routing                                          |
| Next.js page      | `/company/[ticker]`                    | Per-company ESG profile                                                           |
| Next.js page      | `/portfolio`                           | Synthetic 50-corporate loan-book rollup demo                                      |
| Snowflake SQL API | `GET /api/disclosure?company=<ticker>` | Backend for dashboard pages                                                       |

### Third-Party Dependencies

| Dependency                    | Purpose                           | Risk Level                     | Alternative                         |
| ----------------------------- | --------------------------------- | ------------------------------ | ----------------------------------- |
| Anthropic API (Claude Sonnet) | Primary LLM extraction            | Medium — pricing + rate limits | Mistral Large fallback              |
| Mistral API                   | Fallback / FR-language edge cases | Low                            | Claude only (degraded multilingual) |
| Snowflake free trial          | Warehouse                         | High — 30-day expiry           | DuckDB + dbt-duckdb adapter         |
| Airflow 2.10 (Docker)         | Orchestration                     | Low                            | Prefect; or naive cron scripts      |
| dbt-core 1.9                  | Transformations                   | Low                            | Pure SQL scripts (much weaker)      |
| Next.js 16                    | Dashboard                         | Low                            | Streamlit fallback (5h saved)       |
| Vercel                        | Dashboard hosting                 | Low                            | Static export to GitHub Pages       |
| pdfplumber + pypdf2           | PDF text extraction               | Medium — layout variance       | Marker / docling for harder cases   |
| pydantic v2                   | Schema validation                 | Low                            | manual JSON schema                  |

---

## 5. Edge Cases & Error Handling

### What can go wrong?

| Scenario                                              | Expected Behavior                                                                                                                                                      | Priority |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| PDF download fails (timeout, blocked, geo-restricted) | Retry with backoff (3x); on final fail mark `ingestion_failed` in DAG state, do NOT skip silently                                                                      | P0       |
| LLM returns malformed JSON / refuses                  | Pydantic validation catches; fallback to Mistral; on second fail mark metric as `extraction_failed` with diagnostic                                                    | P0       |
| ESRS metric value in image / chart only (no text)     | Skip metric, write `extraction_method: 'unsupported_format'` to fact row                                                                                               | P1       |
| Multilingual mismatch (PDF claimed FR, mostly EN)     | Detect via langdetect on first 5 pages; tag actual language in fact row                                                                                                | P1       |
| Snowflake credit exhaustion (free trial ends)         | Pipeline exits with clear error; README documents the trial-end pivot to DuckDB                                                                                        | P0       |
| Confidence score < 0.80                               | Route to `mart_disclosure_review_queue`; never silently land in published mart                                                                                         | P0       |
| Same disclosure ingested twice (duplicate DAG run)    | Idempotent: composite key `(company_id, metric_id, period_id, model_used)` enforces single fact row; new extraction overwrites only if `extraction_timestamp` is newer | P0       |
| LLM hallucinates a metric value not in PDF            | Source citation (page + snippet) lets human reviewer verify; flagged by quality test `metric_value_in_source_text`                                                     | P0       |
| dbt test fails                                        | DAG fails the `dbt test` task, blocks downstream, alerts via Airflow notification                                                                                      | P0       |
| Network disconnect mid-extraction                     | Resume from last checkpoint (per-PDF checkpointing in Airflow XCom or filesystem)                                                                                      | P1       |

### Security Considerations

- [ ] All API keys (Anthropic, Mistral, Snowflake) in `.env`, never committed
- [ ] `.env.example` documents required keys without values
- [ ] No bank-confidential data ingested (CAC 40 / DAX 40 reports are public)
- [ ] Synthetic loan book is clearly labeled "synthetic; no real bank data"
- [ ] Snowflake account uses MFA (per Snowflake free trial default)
- [ ] Vercel deployment uses Vercel-managed env vars; nothing baked into client bundle

---

## 6. Testing Strategy

### Unit tests (target: 80%+ coverage on `src/extraction` and `src/validation`)

- [ ] PDF parsing: extract text from CAC 40 sample (real PDF)
- [ ] Pydantic schema validation for each ESRS metric type (numeric, text, date, boolean, categorical)
- [ ] Confidence scoring logic: deterministic given (logprob, structural_pass, langdetect_match)
- [ ] Source-citation extraction: page-finding from extracted snippet
- [ ] Language detection on multilingual edge cases

### Integration tests

- [ ] `extract_esrs` DAG end-to-end on a fixed sample of 3 PDFs (1 FR / 2 EN), asserting metric counts + confidence ranges
- [ ] dbt run + dbt test: full pipeline executes against test schema in Snowflake; all tests pass
- [ ] Snowflake connection + write + read round-trip
- [ ] Confidence routing: synthetic metrics with score 0.50 / 0.79 / 0.81 land in correct mart

### E2E tests (critical paths only)

- [ ] `make demo` cold-start: clone → install → env → docker-compose up → trigger DAG → see data in dashboard, all under 15 min
- [ ] Dashboard `/company/[ticker]` page renders with real Snowflake-backed data
- [ ] Loom-walkthrough script: scripted demo flow that I (Pyae) can replay in technical screen

### What NOT to test

- LLM extraction accuracy beyond the gold set — that's the gold-set's job
- Snowflake itself (we trust the platform)
- Next.js framework internals
- Anthropic / Mistral SDK retries (we trust the SDK + add our own outer retry)
- Edge-case PDFs we don't ingest (e.g., scanned-image-only sustainability reports — out of scope)

---

## 7. Milestones & Build Order

### Weekend 1 — Foundation + Extraction (target: 15-18 hrs)

- [ ] **Setup** (2h): Snowflake free trial, Anthropic API key, Mistral API key, GitHub repo init, Docker Compose for Airflow, .env.example, smoke test
- [ ] **PDF ingestion** (3-4h): Airflow `ingest_pdfs` DAG → 30 CAC 40 sustainability PDFs to `/data/raw/`
- [ ] **ESRS schema** (2h): Pydantic v2 models for 80 ESRS metrics across 5 ESRS topics (E1, E2, E3, S1, G1) — focused subset, not exhaustive
- [ ] **LLM extraction loop** (6-8h): Claude Sonnet primary, Mistral fallback, structured output, source-citation, confidence scoring — tested on 5 sample PDFs end-to-end
- [ ] **Snowflake schema** (2-3h): DDL for `dim_company`, `dim_metric`, `dim_period`, `fact_disclosure`; bulk-load from staging
- **Gate at end of Weekend 1:**
  - [ ] 30 PDFs ingested, 1,500+ ESRS values landed in Snowflake `raw.disclosure_extracted`
  - [ ] Source citation populated for every row
  - [ ] Confidence score populated for every row
  - [ ] Smoke test green: `pytest tests/smoke.py` passes
  - [ ] CI pipeline (lint + mypy + pytest) green
  - [ ] **DECISION POINT:** if Weekend 1 ran 20+ hrs, drop DAX 40 stretch + Next.js stretch — fall back to Streamlit + CAC 40 only

### Weekend 2 — Modeling + Dashboard + Polish (target: 12-15 hrs)

- [ ] **dbt project** (4-5h): staging + marts, `mart_disclosure_published` / `mart_disclosure_review_queue` split, lineage docs
- [ ] **dbt tests** (1-2h): uniqueness, not_null, accepted_values + ≥3 custom tests (e.g., `metric_value_in_source_text`, `confidence_in_range`, `language_detected`)
- [ ] **Airflow DAG composition** (2h): full pipeline `ingest → extract → load → dbt run → dbt test`
- [ ] **Next.js dashboard** (4-5h): `/company/[ticker]` page + `/portfolio` synthetic loan-book rollup; deploy to Vercel — **fall back to Streamlit (3h) if budget tight**
- [ ] **Gold-set hand-verification** (3-4h): 800 datapoints (50 companies × 16 metrics) verified against PDFs
- [ ] **README + Loom** (2-3h): hero metrics, architecture, methodology + test conditions, portability section, 90-second Loom
- **Gate at end of Weekend 2:**
  - [ ] All 5 quality gates from §10 pass
  - [ ] Public GitHub repo live
  - [ ] Vercel (or Streamlit) dashboard deployed
  - [ ] dbt docs site deployed
  - [ ] Loom video recorded + linked
  - [ ] **READY TO SHIP** to recruiter

### Phase 3 — Polish & Ship (post Weekend 2; ~3-5 hrs)

- [ ] Read-through pass on README — kill any fragile claim, tighten any unsupported number
- [ ] Cross-link from Pyae's portfolio site (pseonkyaw.dev)
- [ ] Update master CV (`cv.md`) with CSRD-Lake as lead Cloud Data Engineering project
- [ ] Build the Cloud Data Engineer CV variant (LaTeX) using the existing career-ops pipeline

---

## 8. Out of Scope (Explicitly)

- **NOT building:** German (DE) or Spanish (ES) extraction — v2 only
- **NOT building:** Multi-tenant / RBAC / production auth — portfolio piece, not SaaS
- **NOT building:** Real bank loan-book (only synthetic 50-corporate demo)
- **NOT building:** TCFD / ISSB / Pillar 3 cross-walk — single-framework (CSRD/ESRS) only
- **NOT building:** Real-time streaming ingestion — batch-only on manual DAG triggers
- **NOT building:** Production observability stack (Datadog, Grafana, Prometheus) — basic Airflow + Snowflake logs only
- **NOT building:** SOC 2 controls, data-encryption-at-rest beyond Snowflake defaults, audit-grade access control
- **NOT building:** Image-only / chart-only ESRS metric extraction — text-only PDFs in v1
- **NOT building:** Fine-tuned LLM — base Claude Sonnet + Mistral Large only
- **NOT building:** Vendor displacement claim ("replaces MSCI") — explicitly killed by /moat-check
- **Will revisit in v2:** DE + ES coverage, image-table extraction, on-prem LLM (Llama 3 / Mistral local), real bank loan-book pilot, CI/CD against Synapse

---

## 9. Open Questions

- [ ] Q1: 80 ESRS metrics is a lot to schema in 2h — should I scope down to 40 metrics across 3 ESRS topics (E1 climate, S1 workforce, G1 governance)? Decision deferred to start of Weekend 1.
- [ ] Q2: Should the dashboard live at a subdomain of pseonkyaw.dev or at vercel.app? Vercel default is fine if subdomain wiring eats >1h.
- [ ] Q3: Snowflake free trial gives $400 credit — is that enough for the build + 2 weeks of demo? Cap dbt runs to once per development session; estimate $20-40 actual spend.
- [ ] Q4: Loom or asciinema for the demo recording? Loom for screen share + voiceover; asciinema if fully terminal-driven. Likely Loom.

---

## 10. Quality Gates (must pass before "ship to recruiter")

These are non-negotiable. Each is checked at end of Weekend 2.

1. ✅ README has explicit test conditions for every numeric claim (gold-set size, language split, metric distribution, hardware/network assumptions for the <15 min cold-start)
2. ✅ No fragile claims — zero "replaces vendor X" framings, zero inflated counts, every number traced to a verified source
3. ✅ Source citation per extracted ESRS metric (page number + extraction snippet visible in `fact_disclosure.source_citation`)
4. ✅ Confidence-score per metric implemented; <0.80 threshold routes to `mart_disclosure_review_queue`
5. ✅ Portability section in README explicitly maps Snowflake → Synapse, Airflow → ADF, Claude → Azure OpenAI with `dbt-snowflake` ↔ `dbt-synapse` rationale
6. ✅ dbt tests passing (uniqueness, not_null, accepted_values + ≥3 custom)
7. ✅ End-to-end run reproducible from cold start (clone → `make demo` → data visible in dashboard, all <15 min)
8. ✅ Loom walkthrough recorded (~90 sec) showing schema + lineage + extraction sample

---

## 11. Approval

- [ ] **PRD reviewed and understood** — I (Seon) confirm the requirements are clear
- [ ] **Architecture approved** — The technical approach makes sense
- [ ] **Scope locked** — No features will be added during build without updating this PRD
- [ ] **Killed claims acknowledged** — I will refuse any "replaces vendor X" copy

> **Once approved, this PRD becomes the source of truth. Every feature, every endpoint, every component traces back to a user story above. If it's not in the PRD, it's not getting built.**

---

## Appendix A — Validation gap (acknowledged risk)

Per `/prfaq` 2026-04-30, the recruiter's actual mission pipeline math was NOT validated before scaffolding. User accepted this risk on the bet that the architectural pattern (Snowflake + dbt + Airflow + multilingual GenAI extraction) translates beyond CSRD framing to any regulated-data-ingestion role. **If the recruiter's pipeline turns out to be Workiva/SAP-implementation-heavy and CSRD-Lake's Snowflake/dbt framing doesn't fit, the artifact still demonstrates general modern-data-stack proficiency — fallback positioning is "regulated-data ingestion pipeline reference implementation," with CSRD as the demonstration domain.**

---

## Appendix B — Decision log

| Date       | Decision                                                                                | Rationale                                                                                                                    |
| ---------- | --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 2026-04-30 | CSRD-Lake locked as portfolio concept                                                   | /brainstorm Reverse Brainstorm round 1-4                                                                                     |
| 2026-04-30 | Cost-displacement claim killed                                                          | /moat-check: Briink ships exact extraction at €195/mo, MSCI's value is curated ratings not parsing, EU Omnibus shrinks scope |
| 2026-04-30 | "Capgemini Sustainability Data Hub / PwC ESG Reporting Manager pattern" framing adopted | Verifiable, defensible, matches actual recruiter-pitch lane                                                                  |
| 2026-04-30 | TJM target €650/day starting ask                                                        | Free-Work IDF medians 5-10yr €616, hybrid premium justifies +€34                                                             |
| 2026-04-30 | FR + EN only for v1                                                                     | PRFAQ Q8 scope-cut to fit 30h budget                                                                                         |
| 2026-04-30 | Confidence-score + human-review queue                                                   | PRFAQ Q7 risk mitigation for accuracy generalization                                                                         |
| 2026-04-30 | Next.js dashboard, Streamlit fallback                                                   | User chose polish; explicit fallback in budget overrun                                                                       |
| 2026-04-30 | Snowflake free trial, DuckDB fallback                                                   | Real cloud account for recruiter screenshots                                                                                 |
| 2026-04-30 | Skipped pre-build recruiter validation                                                  | User-acknowledged risk; portfolio impact broader than CSRD framing                                                           |
