import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "outline" | "published" | "review" | "muted";

const variantClass: Record<Variant, string> = {
  default: "bg-primary text-primary-foreground",
  outline: "bg-transparent border text-foreground",
  published:
    "bg-confidence-published/12 text-confidence-published border border-confidence-published/30",
  review:
    "bg-confidence-review/12 text-confidence-review border border-confidence-review/35",
  muted: "bg-muted text-muted-foreground",
};

export function Badge({
  variant = "default",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5",
        "text-xs font-medium uppercase tracking-wide",
        variantClass[variant],
        className,
      )}
      {...props}
    />
  );
}
