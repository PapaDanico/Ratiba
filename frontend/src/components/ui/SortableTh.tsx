import type { SortState } from "@/lib/useSort";

/** A clickable column header that cycles sort asc → desc → none, with a glyph. */
export function SortableTh<K extends string>({
  label,
  col,
  sort,
  onSort,
}: {
  label: string;
  col: K;
  sort: SortState<K>;
  onSort: (key: K) => void;
}) {
  const active = sort?.key === col;
  return (
    <button
      type="button"
      onClick={() => onSort(col)}
      className="inline-flex items-center font-medium hover:text-dn-dark"
      data-testid={`sort-${col}`}
    >
      {label}
      {active ? (
        <span className="ml-1 text-dn-navy-deep">{sort!.dir === "asc" ? "▲" : "▼"}</span>
      ) : (
        <span className="ml-1 text-dn-muted/40">↕</span>
      )}
    </button>
  );
}
