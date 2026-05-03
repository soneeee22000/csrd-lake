import { Info } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

/**
 * Inline explainer that appears alongside confidence-routed metrics.
 *
 * The dashboard's amber/green badges only mean "the system has internal
 * signals suggesting this is plausible" — not "this value has been
 * verified correct". This card spells out what the 0–1 score actually
 * composes so a recruiter / stakeholder doesn't read more certainty into
 * the green pill than the system is claiming.
 */
export function ConfidenceExplainer() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Info aria-hidden className="size-4 text-muted-foreground" />
          <CardTitle className="text-base">
            What does the confidence score mean?
          </CardTitle>
        </div>
        <CardDescription>
          A composite of four internal signals — not a claim of factual
          correctness. The source citation on every row is the actual
          verification handle.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3">
          <div className="space-y-1">
            <div className="font-medium">1. LLM self-rating</div>
            <p className="text-muted-foreground leading-relaxed">
              The model rates its own certainty in [0, 1]. Useful but weak alone
              — models hallucinate confidently.
            </p>
          </div>
          <div className="space-y-1">
            <div className="font-medium">2. Structural pass</div>
            <p className="text-muted-foreground leading-relaxed">
              Output parsed into a valid Pydantic <code>ESRSMetric</code> shape.
              Hard fail → score is 0.
            </p>
          </div>
          <div className="space-y-1">
            <div className="font-medium">3. Snippet contains value</div>
            <p className="text-muted-foreground leading-relaxed">
              The verbatim source text we returned literally contains the
              extracted value. Strong circumstantial evidence; failure halves
              the score.
            </p>
          </div>
          <div className="space-y-1">
            <div className="font-medium">4. Language match</div>
            <p className="text-muted-foreground leading-relaxed">
              Manifest-claimed language matches detected language (cross-check
              via langdetect — placeholder in v1, always passing).
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-baseline gap-2 pt-2 border-t">
          <Badge variant="published">≥ 0.80 · published mart</Badge>
          <Badge variant="review">&lt; 0.80 · human review queue</Badge>
          <span className="text-xs text-muted-foreground">
            · routing is automatic, never silent
          </span>
        </div>

        <p className="text-xs text-muted-foreground leading-relaxed">
          <span className="font-medium text-foreground">
            What the score doesn&apos;t catch:
          </span>{" "}
          column-confusion in tables (extracted FY2023 instead of FY2024), unit
          mistakes (kt read as tonnes), or values picked from chart captions
          instead of the disclosure proper. The custom dbt test{" "}
          <code>metric_value_in_source_text</code> catches LLM normalisations
          (e.g. &ldquo;129 million&rdquo; → 129000000) — currently flagging 14
          rows in the warehouse for review.
        </p>

        <p className="text-xs text-muted-foreground leading-relaxed">
          <span className="font-medium text-foreground">
            How correctness is actually verified:
          </span>{" "}
          every row carries{" "}
          <code className="font-mono">(source_page, source_snippet)</code>. A
          human can open the source PDF at the cited page and verify any value
          in seconds. The 800-datapoint hand-verified gold-set (see README,
          planned v1.1) is what would let us claim a percentage accuracy — until
          then, treat published-mart values as <em>system-validated</em>, not{" "}
          <em>human-validated</em>.
        </p>
      </CardContent>
    </Card>
  );
}
