import { Button } from "./Button";

export function Pager({
  page,
  setPage,
  pageCount,
  total,
  pageSize,
}: {
  page: number;
  setPage: (p: number) => void;
  pageCount: number;
  total: number;
  pageSize: number;
}) {
  if (pageCount <= 1) return null;
  const from = page * pageSize + 1;
  const to = Math.min(total, (page + 1) * pageSize);
  return (
    <nav
      aria-label="Pagination"
      className="mt-4 flex items-center justify-between gap-3 text-sm text-dn-muted"
    >
      <span data-testid="pager-range">
        {from}–{to} of {total}
      </span>
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setPage(page - 1)}
          disabled={page === 0}
          data-testid="pager-prev"
        >
          ← Prev
        </Button>
        <span className="font-mono">
          {page + 1}/{pageCount}
        </span>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setPage(page + 1)}
          disabled={page >= pageCount - 1}
          data-testid="pager-next"
        >
          Next →
        </Button>
      </div>
    </nav>
  );
}
