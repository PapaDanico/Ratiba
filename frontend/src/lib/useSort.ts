import { useState } from "react";

export type SortDir = "asc" | "desc";
export type SortState<K extends string> = { key: K; dir: SortDir } | null;

/**
 * Tiny client-side table sort. Click a column to cycle: asc → desc → none.
 * Pure (returns a sorted copy); accessors map a row to a comparable value.
 */
export function useSort<K extends string>(initial: SortState<K> = null) {
  const [sort, setSort] = useState<SortState<K>>(initial);

  function toggle(key: K) {
    setSort((prev) => {
      if (!prev || prev.key !== key) return { key, dir: "asc" };
      if (prev.dir === "asc") return { key, dir: "desc" };
      return null; // third click clears the sort
    });
  }

  function sorted<T>(rows: T[], accessors: Record<K, (row: T) => string | number>): T[] {
    if (!sort) return rows;
    const get = accessors[sort.key];
    const factor = sort.dir === "asc" ? 1 : -1;
    return [...rows].sort((a, b) => {
      const va = get(a);
      const vb = get(b);
      if (va < vb) return -1 * factor;
      if (va > vb) return 1 * factor;
      return 0;
    });
  }

  return { sort, toggle, sorted };
}
