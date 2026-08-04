import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tone = "green" | "amber" | "red" | "navy" | "neutral";

const toneClasses: Record<Tone, string> = {
  green: "bg-dn-green/10 text-dn-green-deep border-dn-green/30",
  amber: "bg-dn-amber-lt text-dn-amber-deep border-dn-amber/60",
  red: "bg-dn-red/10 text-dn-red border-dn-red/30",
  navy: "bg-dn-navy-lt text-dn-navy-deep border-dn-navy/30",
  neutral: "bg-dn-sand/60 text-dn-muted border-dn-muted/20",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2.5 py-0.5 text-xs font-medium tracking-wide",
        toneClasses[tone],
      )}
    >
      {children}
    </span>
  );
}
