import type { DisclosureMetric, EsrsTopic } from "@/lib/data";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ConfidenceBadge } from "@/components/confidence-badge";
import { formatMetricValue } from "@/lib/utils";

const TOPIC_LABEL: Record<EsrsTopic, string> = {
  E1: "E1 — Climate change",
  E2: "E2 — Pollution",
  E3: "E3 — Water and marine resources",
  S1: "S1 — Own workforce",
  G1: "G1 — Business conduct",
};

export function MetricTable({
  topic,
  metrics,
}: {
  topic: EsrsTopic;
  metrics: DisclosureMetric[];
}) {
  if (metrics.length === 0) {
    return null;
  }
  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h2>{TOPIC_LABEL[topic]}</h2>
        <span className="text-xs text-muted-foreground font-mono">
          {metrics.length} metric{metrics.length === 1 ? "" : "s"}
        </span>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[26ch]">Metric</TableHead>
            <TableHead className="w-[18ch]">Value</TableHead>
            <TableHead className="w-[12ch]">Confidence</TableHead>
            <TableHead className="w-[14ch]">Model</TableHead>
            <TableHead>Source</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {metrics.map((m) => (
            <TableRow key={m.id}>
              <TableCell>
                <div className="font-medium text-foreground">
                  {m.metricName}
                </div>
                <div className="text-xs text-muted-foreground font-mono mt-0.5">
                  {m.esrsDisclosure}
                </div>
              </TableCell>
              <TableCell className="font-mono">
                {formatMetricValue(m.valueNumeric, m.valueText, m.unit)}
              </TableCell>
              <TableCell>
                <ConfidenceBadge score={m.confidenceScore} />
              </TableCell>
              <TableCell>
                <Badge
                  variant={
                    m.extractionModel === "claude-sonnet-4-6"
                      ? "outline"
                      : "muted"
                  }
                  className="font-mono normal-case"
                >
                  {m.extractionModel === "claude-sonnet-4-6"
                    ? "claude"
                    : "mistral"}
                </Badge>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                <details className="cursor-pointer">
                  <summary className="hover:text-foreground transition-colors">
                    p.{m.sourcePage}
                  </summary>
                  <blockquote className="mt-2 border-l-2 pl-3 italic">
                    {m.sourceSnippet}
                  </blockquote>
                </details>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </section>
  );
}
