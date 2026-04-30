# Security

CSRD-Lake is a portfolio reference implementation, **not a production system**. It does not implement bank-grade security controls.

## What this repo does NOT do

- ❌ No authentication / RBAC on the dashboard or API surface
- ❌ No SOC 2 / ISO 27001 / HDS controls
- ❌ No bank-confidential data ingestion (CAC 40 / DAX 40 sustainability reports are public)
- ❌ No customer PII handling
- ❌ No audit logging beyond Airflow's built-in task logs and Snowflake's query history

## Reporting a vulnerability

If you find a security issue in any code in this repo (e.g., a path traversal in the downloader, a SQL-injection seam in the loader, an API-key leak), please **do not** open a public issue. Instead:

- Email: `pyaesonekyaw101010@gmail.com`
- Subject line: `[CSRD-Lake security]`

I will respond within 7 days.

## Hardening notes if you fork this for actual production use

1. **Move secrets out of `.env`** — use Azure Key Vault / AWS Secrets Manager / GCP Secret Manager.
2. **Replace `password` Snowflake auth** with key-pair or SSO (Azure AD / Okta).
3. **Sandbox the LLM calls** — Anthropic / Mistral may receive corporate disclosures with embedded prompt-injection attempts in scraped PDFs. Use Anthropic's prompt-cache + the `anthropic-version` header pinning.
4. **Validate downloaded PDFs deeper than magic bytes** — add MIME sniffing + virus scan (ClamAV / Defender) before extraction.
5. **Add row-level security in Snowflake** — `mart_disclosure_review_queue` may contain low-confidence values that should not surface to consumers without role-gating.
6. **Pin all dependencies + run `pip-audit` weekly in CI.**
7. **Enable Snowflake network policies** to restrict access to known CIDR ranges.
