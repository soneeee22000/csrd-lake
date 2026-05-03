import Link from "next/link";
import { ArrowRight } from "lucide-react";
import {
  COMPANIES,
  getCompaniesWithData,
  getCompaniesPendingIngestion,
  SNAPSHOT_EXTRACTED_AT,
} from "@/lib/data";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const metadata = {
  title: "Companies",
  description:
    "FY2024 ESG profiles for CAC 40 companies with extracted disclosures in the CSRD-Lake warehouse.",
};

export default function CompaniesPage() {
  const ingested = getCompaniesWithData();
  const pending = getCompaniesPendingIngestion();
  const extractedDate = new Date(SNAPSHOT_EXTRACTED_AT)
    .toISOString()
    .slice(0, 10);

  return (
    <div className="container-page space-y-12">
      <section className="max-w-3xl space-y-4">
        <Badge variant="outline">
          CAC 40 — FY2024 — extracted {extractedDate}
        </Badge>
        <h1>Companies</h1>
        <p className="text-lg text-muted-foreground leading-relaxed">
          {ingested.length} of {COMPANIES.length} CAC 40 companies in the
          manifest have a full FY2024 ESG profile in the warehouse. Each profile
          groups extracted ESRS metrics by topic and shows the confidence score,
          model attribution, and source-page citation for every value.
        </p>
        <p className="text-sm text-muted-foreground">
          Need the bigger picture first?{" "}
          <Link
            href="/"
            className="text-primary underline-offset-4 hover:underline"
          >
            Read the project landing page
          </Link>{" "}
          · or jump to the{" "}
          <Link
            href="/portfolio"
            className="text-primary underline-offset-4 hover:underline"
          >
            portfolio rollup
          </Link>
          .
        </p>
      </section>

      <section className="space-y-4">
        <div className="flex items-baseline justify-between">
          <h2>Profiles available</h2>
          <span className="font-mono text-xs text-muted-foreground">
            {ingested.length} of {COMPANIES.length}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {ingested.map((company) => (
            <Link
              key={company.ticker}
              href={`/company/${company.ticker}`}
              className="group focus:outline-none focus-visible:ring-2 focus-visible:ring-primary rounded-xl"
            >
              <Card className="h-full">
                <CardHeader>
                  <div className="flex items-center justify-between gap-3">
                    <CardTitle>{company.name}</CardTitle>
                    <Badge variant="outline" className="font-mono">
                      {company.ticker}
                    </Badge>
                  </div>
                  <CardDescription>
                    {company.sector} · {company.country} · reporting in{" "}
                    {company.language.toUpperCase()}
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>View ESG profile</span>
                  <ArrowRight
                    aria-hidden
                    className="size-4 transition-transform group-hover:translate-x-1"
                  />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      {pending.length > 0 && (
        <section className="space-y-3 max-w-3xl">
          <h2 className="text-base font-medium text-muted-foreground">
            Manifest scope · pending ingestion
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            The full manifest at{" "}
            <code className="font-mono text-xs">
              src/csrd_lake/ingestion/data/cac40.toml
            </code>{" "}
            also includes {pending.length} companies whose sustainability PDFs
            have not yet been ingested:
          </p>
          <div className="flex flex-wrap gap-2">
            {pending.map((company) => (
              <Badge
                key={company.ticker}
                variant="outline"
                className="font-mono text-xs"
                title={`${company.name} — ingestion pending`}
              >
                {company.ticker} · {company.name}
              </Badge>
            ))}
          </div>
          <p className="text-xs text-muted-foreground">
            Ingestion is a one-line manifest update + ~$0.50 LLM cost per
            company once a known PDF URL is set.
          </p>
        </section>
      )}
    </div>
  );
}
