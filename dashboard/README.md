# CSRD-Lake Dashboard

Next.js 16 + TypeScript + Tailwind v4 dashboard for the CSRD-Lake portfolio reference implementation.

> **Data source:** real LLM-extracted ESRS metrics from 3 CAC 40 sustainability reports. The committed snapshot at `lib/data/disclosures.json` is exported from the warehouse by `scripts/export_dashboard_data.py` (DuckDB or Snowflake — same JSON shape, same content). The current snapshot was sourced from Snowflake; the `warehouse` field in the JSON records which engine answered the query.

## Pages

| Route               | What it shows                                                                                                   |
| ------------------- | --------------------------------------------------------------------------------------------------------------- |
| `/`                 | Project intro + grid of all 10 manifest companies                                                               |
| `/company/[ticker]` | Per-company ESG profile — metrics grouped by ESRS topic, confidence routing badges, expandable source citations |
| `/portfolio`        | Synthetic 10-corporate loan-book rollup — total exposure, total Scope 1, weighted intensity per €M              |

Pre-rendered at build time via `generateStaticParams()` — each company page is a static file.

## Stack

- **Next.js 16** (App Router, Server Components by default, Turbopack dev)
- **React 19**
- **TypeScript 5.7** strict, `noUncheckedIndexedAccess`
- **Tailwind v4** with `@theme` design tokens (no raw color classes; tokens only)
- **Lucide React** for icons (no emoji per global standards)
- shadcn-style local primitives (`components/ui/`) — `Card`, `Table`, `Badge`

## Design tokens

3 colors + 2 confidence-routing accents, defined in `app/globals.css`:

| Token                                       | Use                             |
| ------------------------------------------- | ------------------------------- |
| `--color-primary`                           | Brand (deep forest, CSRD theme) |
| `--color-foreground` / `--color-background` | Body                            |
| `--color-muted`                             | Surfaces, table headers         |
| `--color-confidence-published`              | Confidence ≥ 0.80 — green       |
| `--color-confidence-review`                 | Confidence < 0.80 — amber       |

Two font families: `Geist Sans` (UI) + `Geist Mono` (tickers, numbers). No gradient backgrounds.

## Local development

```bash
cd dashboard
pnpm install      # or npm install / yarn install
pnpm dev          # http://localhost:3000
pnpm typecheck    # tsc --noEmit
pnpm lint         # next lint
pnpm build        # production build
```

Node 20+ required.

## Deploy to Vercel

```bash
vercel --prod
```

The dashboard is fully self-contained — no env vars needed for v1 (data is bundled). Vercel auto-detects Next.js and uses the right build command.

## Switching to live Snowflake reads at request time (v1.1 plan)

The dashboard already serves Snowflake-sourced data (via the JSON snapshot exported by `scripts/export_dashboard_data.py --source snowflake`). v1.1 would replace the static accessors in `lib/data.ts` with Server Component fetches that hit `mart_disclosure_published` on every request, trading static-build performance for live freshness:

```typescript
// lib/data.ts (v1.1 sketch)
import { Client } from "snowflake-sdk";

export async function getDisclosuresByTicker(
  ticker: string,
): Promise<CompanyDisclosures | undefined> {
  const conn = new Client({
    account: process.env.SNOWFLAKE_ACCOUNT!,
    // ...
  });
  const rows = await conn.execute(
    "SELECT * FROM marts.mart_disclosure_published WHERE company_ticker = ?",
    [ticker],
  );
  // ... map to CompanyDisclosures
}
```

Component code stays unchanged.

## Project layout

```
dashboard/
├── app/
│   ├── layout.tsx              global shell, header, footer
│   ├── page.tsx                home — company grid
│   ├── globals.css             design tokens + base layer
│   ├── company/[ticker]/page.tsx     per-company ESG profile (static)
│   ├── portfolio/page.tsx            synthetic loan-book rollup
│   └── not-found.tsx
├── components/
│   ├── ui/                     shadcn-style primitives (Card, Table, Badge)
│   ├── metric-table.tsx        ESRS-topic-grouped table with routing badges
│   └── confidence-badge.tsx    routing-aware badge for the 0.80 threshold
├── lib/
│   ├── data.ts                 typed accessors over the disclosures.json snapshot
│   └── utils.ts                cn(), formatMetricValue(), confidenceBand()
├── package.json
├── tsconfig.json
├── next.config.ts
├── postcss.config.mjs
├── eslint.config.mjs
└── README.md                   you are here
```
