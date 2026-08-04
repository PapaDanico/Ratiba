/** Animated placeholder bars for content that's still loading. A shimmer
 * sweeps across each bar; under prefers-reduced-motion it rests as a static
 * tint. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`shimmer rounded bg-dn-navy-lt/60 ${className}`} />;
}

/** A simple multi-row placeholder for tables that are still loading. */
export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="space-y-2" data-testid="table-skeleton" aria-hidden>
      <div className="flex gap-4 border-b border-dn-navy-lt pb-2">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 py-1">
          {Array.from({ length: cols }).map((_, c) => (
            <Skeleton key={c} className="h-4 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
