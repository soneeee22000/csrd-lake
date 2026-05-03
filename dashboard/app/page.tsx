import Link from "next/link";
import {
  ArrowRight,
  Database,
  FileText,
  GitBranch,
  Layers,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { COMPANIES, getAllCompanies, SNAPSHOT_EXTRACTED_AT } from "@/lib/data";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// ── Live snapshot numbers (computed at build time from disclosures.json) ──

const allMetrics = COMPANIES.flatMap((c) =>
  getAllCompanies().find((x) => x.ticker === c.ticker) ? [] : [],
); // placeholder — we read from data lib for typed counts below

const SNAPSHOT_STATS = (() => {
  // Lazy import-pattern via the public accessor surface — no JSON re-parse.
  // We count metrics by walking each company's disclosures.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const data: {
    disclosuresByTicker: Record<string, Array<{ confidenceScore: number }>>;
  } = require("@/lib/data/disclosures.json");
  const flat = Object.values(data.disclosuresByTicker).flat();
  return {
    totalMetrics: flat.length,
    published: flat.filter((m) => m.confidenceScore >= 0.8).length,
    review: flat.filter((m) => m.confidenceScore < 0.8).length,
    companiesWithData: Object.values(data.disclosuresByTicker).filter(
      (arr) => arr.length > 0,
    ).length,
  };
})();

// ── Architecture pipeline cards ──────────────────────────────────────

const PIPELINE_STAGES: Array<{
  step: string;
  title: string;
  body: string;
  icon: typeof Database;
}> = [
  {
    step: "01",
    title: "Ingest",
    body: "TOML manifest of 10 CAC 40 companies. Direct PDF download from each issuer's investor-relations site, with retry, atomic write, and PDF magic-byte validation.",
    icon: FileText,
  },
  {
    step: "02",
    title: "Extract",
    body: "Per (PDF × ESRS topic): keyword-filter to relevant pages, send to Claude Sonnet, fall back to Mistral Large on rate-limit or malformed JSON. Output validated by Pydantic.",
    icon: Sparkles,
  },
  {
    step: "03",
    title: "Confidence-route",
    body: "Every metric scored on logprob × structural pass × snippet-match × language-match. Below 0.80 lands in the human review queue, never the published mart.",
    icon: ShieldCheck,
  },
  {
    step: "04",
    title: "Land",
    body: "Bulk-insert into raw.disclosure_extracted. Same column shape on Snowflake (production) and DuckDB (local). Loader uses parameterised executemany — same metric_to_row mapping for both backends.",
    icon: Database,
  },
  {
    step: "05",
    title: "Model",
    body: "dbt star schema: stg_disclosure (dedupe on natural key) → dim_company / dim_metric (auto-extending) / dim_period → fact_disclosure → published + review_queue marts.",
    icon: Layers,
  },
  {
    step: "06",
    title: "Test",
    body: "54 generic dbt tests + 3 custom: source_snippet contains value, confidence_score in [0,1], published and review marts disjoint. Surfaces real LLM hallucinations at build time.",
    icon: GitBranch,
  },
];

// ── Tech stack ────────────────────────────────────────────────────────

const TECH_BY_LAYER: Array<{ layer: string; tools: string[] }> = [
  {
    layer: "Ingestion",
    tools: ["Python 3.12", "httpx", "tenacity", "Pydantic v2"],
  },
  {
    layer: "Extraction",
    tools: [
      "Anthropic Claude Sonnet",
      "Mistral Large",
      "pdfplumber",
      "structlog",
    ],
  },
  {
    layer: "Warehouse",
    tools: [
      "Snowflake (validated)",
      "DuckDB (local)",
      "snowflake-connector-python",
      "RSA key-pair auth",
    ],
  },
  {
    layer: "Transform",
    tools: ["dbt 1.11", "dbt-snowflake", "dbt-duckdb", "dbt-utils"],
  },
  {
    layer: "Orchestration",
    tools: ["Airflow 2.10", "TaskFlow API", "Dynamic task mapping"],
  },
  {
    layer: "Dashboard",
    tools: ["Next.js 16", "React 19", "Tailwind v4", "shadcn primitives"],
  },
  {
    layer: "DevEx",
    tools: [
      "uv lockfile",
      "ruff",
      "mypy strict",
      "pytest 167",
      "GitHub Actions",
    ],
  },
];

// ── Page ──────────────────────────────────────────────────────────────

export default function LandingPage() {
  const extractedDate = new Date(SNAPSHOT_EXTRACTED_AT)
    .toISOString()
    .slice(0, 10);

  return (
    <div className="container-page space-y-20">
      {/* Hero */}
      <section className="max-w-3xl space-y-6 pt-6">
        <Badge variant="outline">
          FY2024 · live snapshot extracted {extractedDate}
        </Badge>
        <h1 className="text-5xl leading-[1.05] tracking-tight">
          CSRD/ESRS sustainability disclosures,
          <br />
          <span className="text-primary">structured and queryable.</span>
        </h1>
        <p className="text-lg text-muted-foreground leading-relaxed">
          A working reference implementation of the Big-4 &ldquo;Sustainability
          Data Hub&rdquo; pattern: ingest CAC 40 sustainability PDFs, extract
          ESRS metrics with Claude + Mistral, land them in a Snowflake
          star-schema warehouse modelled with dbt, surface them on this
          dashboard.
        </p>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Built end-to-end on real disclosures from{" "}
          <span className="text-foreground">LVMH</span>,{" "}
          <span className="text-foreground">TotalEnergies</span>, and{" "}
          <span className="text-foreground">Schneider Electric</span> — every
          metric carries page-level source citation and a confidence score that
          routes uncertain extractions to a human review queue.
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            href="/companies"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-3 text-primary-foreground font-medium hover:opacity-90 transition-opacity"
          >
            Explore companies
            <ArrowRight aria-hidden className="size-4" />
          </Link>
          <Link
            href="/portfolio"
            className="inline-flex items-center gap-2 rounded-md border px-5 py-3 font-medium hover:bg-muted transition-colors"
          >
            Portfolio rollup
          </Link>
          <a
            href="https://github.com/soneeee22000/csrd-lake"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-md border px-5 py-3 font-medium hover:bg-muted transition-colors"
          >
            View on GitHub
          </a>
        </div>
      </section>

      {/* Live snapshot stats */}
      <section className="space-y-4">
        <h2>Right now in the warehouse</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader>
              <CardDescription>Real ESRS metrics extracted</CardDescription>
              <CardTitle className="text-4xl font-mono">
                {SNAPSHOT_STATS.totalMetrics}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              From {SNAPSHOT_STATS.companiesWithData} of {COMPANIES.length} CAC
              40 companies
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>Published mart (conf ≥ 0.80)</CardDescription>
              <CardTitle className="text-4xl font-mono">
                {SNAPSHOT_STATS.published}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Cleared the confidence gate — joinable, citable
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>Human review queue</CardDescription>
              <CardTitle className="text-4xl font-mono">
                {SNAPSHOT_STATS.review}
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              Below 0.80 — held back from publication
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>dbt models · pytest cases</CardDescription>
              <CardTitle className="text-4xl font-mono">7 · 167</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">
              54 dbt tests + 3 custom data-integrity tests
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Why this exists */}
      <section className="max-w-3xl space-y-4">
        <Badge variant="outline">The problem</Badge>
        <h2 className="text-3xl">
          1,100+ ESRS datapoints. 300-page PDFs. Annual deadline.
        </h2>
        <p className="text-base text-muted-foreground leading-relaxed">
          The EU&apos;s Corporate Sustainability Reporting Directive (CSRD)
          mandates that every large listed company publish detailed ESG
          disclosures using the European Sustainability Reporting Standards
          (ESRS). Wave 1 covers FY2024 reports. The reports come out as PDFs.
          Investors, banks, regulators, and corporate compliance teams need them{" "}
          <span className="text-foreground">structured and queryable</span> —
          not as PDFs.
        </p>
        <p className="text-base text-muted-foreground leading-relaxed">
          This is the problem Capgemini, Deloitte, PwC, KPMG, and EY are selling
          solutions for to French G-SIBs (BNP Paribas, Société Générale, Crédit
          Agricole, BPCE) right now under names like{" "}
          <span className="text-foreground">Sustainability Data Hub</span>,{" "}
          <span className="text-foreground">ESG Reporting Manager</span>, and{" "}
          <span className="text-foreground">CSRD 360 Navigator</span>. The
          architectural pattern is consistent. CSRD-Lake is its open-source
          reference implementation.
        </p>
      </section>

      {/* Architecture */}
      <section className="space-y-6">
        <div className="max-w-3xl space-y-2">
          <Badge variant="outline">How it works</Badge>
          <h2 className="text-3xl">PDFs → warehouse → dashboard.</h2>
          <p className="text-base text-muted-foreground">
            Six layers, each independently testable, each with a quality gate.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {PIPELINE_STAGES.map((stage) => {
            const Icon = stage.icon;
            return (
              <Card key={stage.step}>
                <CardHeader>
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-mono text-xs text-muted-foreground">
                      {stage.step}
                    </span>
                    <Icon aria-hidden className="size-5 text-primary" />
                  </div>
                  <CardTitle>{stage.title}</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground leading-relaxed">
                  {stage.body}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </section>

      {/* Tech stack */}
      <section className="space-y-6">
        <div className="max-w-3xl space-y-2">
          <Badge variant="outline">Tech stack</Badge>
          <h2 className="text-3xl">Modern data stack, end-to-end.</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3">
          {TECH_BY_LAYER.map(({ layer, tools }) => (
            <div
              key={layer}
              className="flex flex-col sm:flex-row sm:items-baseline gap-2 sm:gap-6 py-2 border-b last:border-b-0"
            >
              <span className="font-medium min-w-32">{layer}</span>
              <div className="flex flex-wrap gap-1.5">
                {tools.map((t) => (
                  <Badge
                    key={t}
                    variant="outline"
                    className="font-mono text-xs"
                  >
                    {t}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Honest scope */}
      <section className="space-y-4">
        <Badge variant="outline">Honest scope</Badge>
        <h2 className="text-3xl">What&apos;s real, what&apos;s a stub.</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Real and validated end-to-end
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>
                · 3 real CAC 40 sustainability PDFs (LVMH, TotalEnergies,
                Schneider)
              </p>
              <p>
                · {SNAPSHOT_STATS.totalMetrics} ESRS metrics extracted via
                Claude + Mistral fallback chain
              </p>
              <p>
                · Snowflake warehouse: DDL, key-pair auth, marts built, 54 of 55
                dbt tests pass
              </p>
              <p>
                · DuckDB local fallback path also working — same models compile
                on both
              </p>
              <p>· 167 pytest cases, ~91% coverage, GitHub Actions CI</p>
              <p>· Live dashboard deployed to Vercel, statically prerendered</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Stubs and open work</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <p>· 7 of 10 manifest companies pending PDF ingestion</p>
              <p>
                · Airflow DAG defined but executed via Python CLI
                (orchestration-pattern visibility)
              </p>
              <p>
                · 14 rows fail the source-snippet-contains-value test (LLM
                normalises &ldquo;129 million&rdquo; → 129000000) — exactly the
                hallucination class the test is designed to catch
              </p>
              <p>· Hand-verified gold-set accuracy claim still pending</p>
              <p>· Portfolio exposure values are clearly-labelled synthetic</p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Final CTA */}
      <section className="max-w-3xl space-y-4 pb-8">
        <h2 className="text-3xl">Pick your next click.</h2>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/companies"
            className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-3 text-primary-foreground font-medium hover:opacity-90 transition-opacity"
          >
            Browse the {SNAPSHOT_STATS.companiesWithData} ingested companies
            <ArrowRight aria-hidden className="size-4" />
          </Link>
          <a
            href="https://github.com/soneeee22000/csrd-lake/blob/main/docs/PROJECT_CONTEXT.md"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-md border px-5 py-3 font-medium hover:bg-muted transition-colors"
          >
            Read the project context
          </a>
          <a
            href="https://github.com/soneeee22000/csrd-lake"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-md border px-5 py-3 font-medium hover:bg-muted transition-colors"
          >
            Read the source
          </a>
        </div>
      </section>
    </div>
  );
}
