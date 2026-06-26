import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  /** Subtle shadow lift + raise on hover — for interactive/clickable cards
   * (e.g. dashboard attention tiles). Off by default so static panels stay put. */
  interactive?: boolean;
};

export function Card({ className, children, interactive = false, ...rest }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-dn-sand bg-white shadow-sm overflow-hidden",
        interactive &&
          "transition-all duration-150 hover:-translate-y-0.5 hover:shadow-md motion-reduce:transform-none motion-reduce:transition-none",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("bg-dn-sand/50 px-6 pt-4 pb-0", className)}>
      <div className="pb-3">{children}</div>
      {/* Maasai geometric stripe beneath every card header */}
      <div className="tribal-stripe -mx-6" />
    </div>
  );
}

export function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return <h2 className={cn("font-display text-xl text-dn-dark", className)}>{children}</h2>;
}

export function CardBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("p-6", className)}>{children}</div>;
}
