import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { getAllCompanies, SNAPSHOT_EXTRACTED_AT } from "@/lib/data";
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
    "FY2024 ESG profiles for the 10 CAC 40 companies in the CSRD-Lake manifest.",
};

export default function CompaniesPage() {
  const companies = getAllCompanies();
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
          Browse the FY2024 ESG profile of any CAC 40 company in the manifest.
          Three companies have real LLM-extracted disclosures from their
          published sustainability reports; the remaining seven render an empty
          profile (PDF ingestion pending).
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
          <h2>Companies in the manifest</h2>
          <span className="font-mono text-xs text-muted-foreground">
            {companies.length} listed
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {companies.map((company) => (
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
    </div>
  );
}
