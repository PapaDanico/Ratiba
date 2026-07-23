import { useEffect, useMemo, useState } from "react";

/** Client-side pagination for list pages. Keeps the page in range when the
 * underlying list shrinks (filters, deletes) and hides itself entirely for
 * lists that fit on one page (see <Pager />). */
export function usePager<T>(rows: T[], pageSize = 25) {
  const [page, setPage] = useState(0);
  const pageCount = Math.max(1, Math.ceil(rows.length / pageSize));
  useEffect(() => {
    if (page > pageCount - 1) setPage(pageCount - 1);
  }, [page, pageCount]);
  const pageRows = useMemo(
    () => rows.slice(page * pageSize, (page + 1) * pageSize),
    [rows, page, pageSize],
  );
  return { page, setPage, pageCount, pageRows, total: rows.length, pageSize };
}
