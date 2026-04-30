import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { getAllCompanies } from "@/lib/data";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function Home() {
  const companies = getAllCompanies();

  return (
    <div className="container-page space-y-12">
      <section className="max-w-3xl space-y-4">
        <Badge variant="outline">CAC 40 — FY2024 — synthetic v1 dataset</Badge>
        <h1>CSRD-Lake</h1>
        <p className="text-lg text-muted-foreground leading-relaxed">
          End-to-end CSRD/ESRS data pipeline reference implementation —
          Snowflake star schema, dbt models, Airflow orchestration, and
          multilingual GenAI extraction with source citation and audit lineage.
          Same architectural pattern Capgemini&apos;s Sustainability Data Hub
          and PwC&apos;s ESG Reporting Manager deploy at French banks today.
        </p>
        <p className="text-sm text-muted-foreground">
          Pick any company below to see its FY2024 ESG profile, or jump to the{" "}
          <Link
            href="/portfolio"
            className="text-primary underline-offset-4 hover:underline"
          >
            portfolio rollup
          </Link>{" "}
          for a synthetic 10-corporate loan-book view.
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
