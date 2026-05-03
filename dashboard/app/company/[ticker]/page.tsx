import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import {
  getCompaniesWithData,
  getDisclosuresByTicker,
  type EsrsTopic,
} from "@/lib/data";
import { MetricTable } from "@/components/metric-table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { confidenceBand } from "@/lib/utils";

const TOPIC_ORDER: readonly EsrsTopic[] = ["E1", "E2", "E3", "S1", "G1"];

type Params = { ticker: string };

// Pre-render only companies with extracted data — visitors should never
// land on an empty profile. The full manifest is acknowledged on the
// /companies index footnote.
export function generateStaticParams(): Params[] {
  return getCompaniesWithData().map((c) => ({ ticker: c.ticker }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { ticker } = await params;
  const data = getDisclosuresByTicker(ticker);
  if (!data) return { title: "Not found" };
  return {
    title: `${data.company.name} (${data.company.ticker}) — FY${data.fiscalYear} ESG profile`,
    description: `CSRD/ESRS metrics extracted from ${data.company.name}'s FY${data.fiscalYear} sustainability report. ${data.metrics.length} metrics across E1, E2, E3, S1, G1.`,
  };
}

export default async function CompanyPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { ticker } = await params;
  const data = getDisclosuresByTicker(ticker);
  if (!data) notFound();

  const { company, fiscalYear, metrics } = data;

  // Group metrics by ESRS topic, preserving the canonical topic order.
  const byTopic = new Map<EsrsTopic, typeof metrics>();
  for (const topic of TOPIC_ORDER) byTopic.set(topic, []);
  for (const m of metrics) byTopic.get(m.esrsTopic)?.push(m);

  // Routing summary — what % would land in published vs review queue.
  const publishedCount = metrics.filter(
    (m) => confidenceBand(m.confidenceScore) === "published",
  ).length;
  const reviewCount = metrics.length - publishedCount;
  const avgConfidence =
    metrics.length === 0
      ? 0
      : metrics.reduce((acc, m) => acc + m.confidenceScore, 0) / metrics.length;

  return (
    <div className="container-page space-y-10">
      <div className="space-y-3">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft aria-hidden className="size-4" />
          Back to all companies
        </Link>
        <div className="flex flex-wrap items-baseline gap-3">
          <h1>{company.name}</h1>
          <Badge variant="outline" className="font-mono text-sm">
            {company.ticker}
          </Badge>
        </div>
        <p className="text-muted-foreground">
          {company.sector} · {company.country} · FY{fiscalYear} CSRD/ESRS
          disclosures
        </p>
      </div>

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{metrics.length}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Total metrics extracted across all ESRS topics
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="font-mono">
                {(avgConfidence * 100).toFixed(1)}%
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Average confidence score across all metrics
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="text-confidence-published">
                {publishedCount}
              </span>
              <span className="text-muted-foreground"> / </span>
              <span className="text-confidence-review">{reviewCount}</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Published mart vs review queue (threshold: 0.80)
          </CardContent>
        </Card>
      </section>

      <div className="space-y-10">
        {TOPIC_ORDER.map((topic) => {
          const items = byTopic.get(topic) ?? [];
          if (items.length === 0) return null;
          return <MetricTable key={topic} topic={topic} metrics={items} />;
        })}
      </div>
    </div>
  );
}
