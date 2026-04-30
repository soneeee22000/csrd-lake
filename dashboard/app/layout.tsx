import type { Metadata } from "next";
import Link from "next/link";
import { Database } from "lucide-react";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "CSRD-Lake — CSRD/ESRS data pipeline reference implementation",
    template: "%s · CSRD-Lake",
  },
  description:
    "End-to-end CSRD/ESRS data pipeline reference implementation. Reference implementation of the Capgemini Sustainability Data Hub / PwC ESG Reporting Manager pattern. Snowflake + dbt + Airflow + multilingual GenAI extraction.",
  authors: [{ name: "Pyae Sone Kyaw", url: "https://pseonkyaw.dev" }],
  keywords: [
    "CSRD",
    "ESRS",
    "data engineering",
    "Snowflake",
    "dbt",
    "Airflow",
    "Claude",
    "Mistral",
    "sustainability reporting",
    "EU Taxonomy",
  ],
  openGraph: {
    title: "CSRD-Lake — CSRD/ESRS data pipeline reference implementation",
    description:
      "End-to-end CSRD/ESRS data pipeline. Snowflake + dbt + Airflow + multilingual GenAI extraction.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="border-b">
          <div className="container-page py-4 flex items-center justify-between">
            <Link
              href="/"
              className="flex items-center gap-2 text-foreground hover:text-primary transition-colors"
            >
              <Database aria-hidden className="size-5" />
              <span className="font-semibold tracking-tight">CSRD-Lake</span>
            </Link>
            <nav className="flex items-center gap-6 text-sm">
              <Link
                href="/portfolio"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                Portfolio rollup
              </Link>
              <a
                href="https://github.com/soneeee22000/csrd-lake"
                className="text-muted-foreground hover:text-foreground transition-colors"
                target="_blank"
                rel="noreferrer"
              >
                GitHub
              </a>
            </nav>
          </div>
        </header>
        <main>{children}</main>
        <footer className="border-t mt-16">
          <div className="container-page py-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-2 text-sm text-muted-foreground">
            <span>
              CSRD-Lake — portfolio reference implementation. Synthetic data;
              not real corporate disclosures.
            </span>
            <span>
              Built by{" "}
              <a
                href="https://pseonkyaw.dev"
                className="text-foreground hover:text-primary transition-colors"
                target="_blank"
                rel="noreferrer"
              >
                Pyae Sone Kyaw
              </a>
            </span>
          </div>
        </footer>
      </body>
    </html>
  );
}
