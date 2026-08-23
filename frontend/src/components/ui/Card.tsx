import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type CardProps = HTMLAttributes<HTMLDivElement> & { interactive?: boolean };

export function Card({ className, children, interactive = false, ...rest }: CardProps) {
  return (
    <div className={cn(
      "rounded-dn border border-dn-sand-deep/90 bg-dn-sand shadow-dn overflow-hidden",
      interactive && "transition-all duration-200 hover:-translate-y-0.5 hover:border-dn-navy/70 hover:shadow-dn-lg motion-reduce:transform-none motion-reduce:transition-none",
      className,
    )} {...rest}>{children}</div>
  );
}
export function CardHeader({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("border-b border-dn-sand-deep bg-dn-dark-deep/25 px-5 pt-4", className)}><div className="pb-3">{children}</div><div className="tribal-stripe -mx-5" /></div>;
}
export function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return <h2 className={cn("font-body text-sm font-semibold uppercase tracking-[0.12em] text-dn-dark", className)}>{children}</h2>;
}
export function CardBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("p-5", className)}>{children}</div>;
}
