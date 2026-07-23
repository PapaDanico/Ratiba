import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { cn } from "@/lib/cn";
import { Button } from "./Button";

type EmptyStateProps = {
  /** Short headline, e.g. "No crew yet". */
  title: string;
  /** Optional one-line guidance on how to populate this view. */
  hint?: ReactNode;
  /** Single-glyph icon (emoji or node). Defaults to a calm dotted circle. */
  icon?: ReactNode;
  /** Optional next step — a button that takes the user where the data comes from. */
  action?: { label: string; to: string };
  className?: string;
};

/**
 * Calm, centred empty state for tables/lists — an icon, a title, and optional
 * guidance, instead of a bare muted sentence. Keeps the grid feeling finished
 * when there's no data yet.
 */
export function EmptyState({ title, hint, icon = "🗒️", action, className }: EmptyStateProps) {
  return (
    <div
      className={cn("flex flex-col items-center justify-center px-6 py-10 text-center", className)}
      data-testid="empty-state"
    >
      <div
        aria-hidden
        className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-dn-sand/50 text-xl"
      >
        {icon}
      </div>
      <p className="font-display text-lg text-dn-dark">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-sm text-dn-muted">{hint}</p>}
      {action && (
        <Link to={action.to} className="mt-4">
          <Button size="sm" variant="secondary">
            {action.label}
          </Button>
        </Link>
      )}
    </div>
  );
}
