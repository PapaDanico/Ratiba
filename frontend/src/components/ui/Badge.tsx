import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tone = "green" | "amber" | "red" | "steel" | "gold" | "neutral";

const toneClasses: Record<Tone, string> = {
  green: "bg-dn-green/10 text-dn-green border-dn-green/30",
  amber: "bg-dn-gold-lt text-dn-dark border-dn-gold",
  red: "bg-dn-red/10 text-dn-red border-dn-red/30",
  steel: "bg-dn-steel-lt text-dn-steel border-dn-steel/30",
  gold: "bg-dn-gold-lt text-dn-dark border-dn-gold",
  neutral: "bg-dn-fog text-dn-muted border-dn-muted/30",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        toneClasses[tone],
      )}
    >
      {children}
    </span>
  );
}
