import type { Metadata } from "next";
import Link from "next/link";
import { getPortfolioExposures, getPortfolioTotals } from "@/lib/data";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

export const metadata: Metadata = {
  title: "Portfolio rollup",
  description:
    "Synthetic 10-corporate loan-book ESG profile demo. Aggregates Scope 1 emissions and emissions intensity across the CSRD-Lake manifest.",
};

const formatNumber = (n: number): string =>
  new Intl.NumberFormat("en-US").format(n);

const formatMillionsEur = (n: number): string => `€${formatNumber(n)}M`;

export default function PortfolioPage() {
  const exposures = getPortfolioExposures();
  const totals = getPortfolioTotals();

  return (
    <div className="container-page space-y-10">
      <div className="space-y-3 max-w-3xl">
        <Badge variant="outline">
          Synthetic loan book — not real bank data
        </Badge>
        <h1>Portfolio rollup</h1>
        <p className="text-muted-foreground">
          A worked example of how a French bank&apos;s sustainable-finance team
          would aggregate CSRD-extracted Scope 1 emissions across a corporate
          loan book. Exposure figures are illustrative; emissions are pulled
          from the same synthetic dataset as the per-company pages.
        </p>
      </div>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader>
            <CardDescription>Total exposure</CardDescription>
            <CardTitle className="font-mono text-2xl">
              {formatMillionsEur(totals.totalExposureEurMillions)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Total Scope 1 emissions</CardDescription>
            <CardTitle className="font-mono text-2xl">
              {formatNumber(totals.totalScope1Emissions)} tCO₂e
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Weighted intensity</CardDescription>
            <CardTitle className="font-mono text-2xl">
              {formatNumber(totals.weightedEmissionsIntensity)} tCO₂e/€M
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Companies covered</CardDescription>
            <CardTitle className="font-mono text-2xl">
              {totals.companyCount}
              <span className="text-muted-foreground text-base font-normal">
                {" "}
                / {exposures.length}
              </span>
            </CardTitle>
          </CardHeader>
        </Card>
      </section>

      <section className="space-y-4">
        <div className="flex items-baseline justify-between">
          <h2>Per-company breakdown</h2>
          <span className="text-xs text-muted-foreground font-mono">
            {exposures.length} exposures
          </span>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Company</TableHead>
              <TableHead>Sector</TableHead>
              <TableHead className="text-right">Exposure</TableHead>
              <TableHead className="text-right">Scope 1 (tCO₂e)</TableHead>
              <TableHead className="text-right">Intensity (tCO₂e/€M)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {exposures.map((e) => (
              <TableRow key={e.company.ticker}>
                <TableCell>
                  <Link
                    href={`/company/${e.company.ticker}`}
                    className="text-foreground hover:text-primary transition-colors"
                  >
                    <div className="font-medium">{e.company.name}</div>
                    <div className="text-xs text-muted-foreground font-mono mt-0.5">
                      {e.company.ticker}
                    </div>
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {e.company.sector}
                </TableCell>
                <TableCell className="font-mono text-right">
                  {formatMillionsEur(e.exposureEurMillions)}
                </TableCell>
                <TableCell className="font-mono text-right">
                  {e.scope1Emissions !== null
                    ? formatNumber(e.scope1Emissions)
                    : "—"}
                </TableCell>
                <TableCell className="font-mono text-right">
                  {e.emissionsPerEurMillion !== null
                    ? formatNumber(e.emissionsPerEurMillion)
                    : "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>

      <p className="text-xs text-muted-foreground italic">
        Note: this is a portfolio demo, not a real bank loan book. Exposure
        figures are synthetic; emissions values come from the synthetic v1
        dataset documented in the README. Real deployments would source
        exposures from the bank&apos;s loan-management system and emissions from
        the published Snowflake mart_disclosure_published.
      </p>
    </div>
  );
}
