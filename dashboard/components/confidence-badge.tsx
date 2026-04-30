import { Badge } from "@/components/ui/badge";
import { confidenceBand, formatConfidence } from "@/lib/utils";

/**
 * Renders a confidence score as a routing-aware badge.
 * Green when >=0.80 (would land in mart_disclosure_published);
 * amber when <0.80 (would route to mart_disclosure_review_queue).
 */
export function ConfidenceBadge({ score }: { score: number }) {
  const band = confidenceBand(score);
  return (
    <Badge variant={band} title={`Routing: mart_disclosure_${band}`}>
      {formatConfidence(score)}
    </Badge>
  );
}
