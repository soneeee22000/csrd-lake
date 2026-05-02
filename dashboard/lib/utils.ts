import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind class names with conflict-aware deduplication.
 * Standard shadcn-style helper.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format an ESRS metric value for display. Numerics get thousand-separators
 * with the unit appended; text passes through.
 */
export function formatMetricValue(
  valueNumeric: number | null,
  valueText: string | null,
  unit: string | null,
): string {
  if (valueNumeric !== null) {
    const formatted =
      Math.abs(valueNumeric) >= 1000
        ? new Intl.NumberFormat("fr-FR").format(valueNumeric)
        : valueNumeric.toString();
    return unit ? `${formatted} ${unit}` : formatted;
  }
  if (valueText !== null) {
    return valueText;
  }
  return "—";
}

/**
 * Confidence-band routing — mirrors the dbt mart split.
 * Returns the visual-state key, NOT a raw color class.
 */
export function confidenceBand(score: number): "published" | "review" {
  return score >= 0.8 ? "published" : "review";
}

/** Pretty-print a confidence score as a percentage with one decimal. */
export function formatConfidence(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}
