import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tone = "green" | "amber" | "red" | "steel" | "gold" | "neutral";

const toneClasses: Record<Tone, string> = {
  green: "bg-dn-green/10 text-dn-green border-dn-green/30",
  amber: "bg-dn-savanna-lt text-dn-savanna border-dn-savanna/40",
  red: "bg-dn-red/10 text-dn-red border-dn-red/30",
  steel: "bg-dn-steel-lt text-dn-steel border-dn-steel/30",
  gold: "bg-dn-gold-lt text-dn-dark border-dn-gold/60",
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
