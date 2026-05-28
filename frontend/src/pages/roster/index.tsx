import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api, ApiError } from "@/lib/api";

type Assignment = {
  duty_day_key: string;
  date_local: string;
  aircraft_reg: string;
  aircraft_type: string;
  sector_ids: string[];
  captain_id: string;
  fo_id: string;
};

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function addDays(iso: string, days: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function dateRange(from: string, to: string): string[] {
  const out: string[] = [];
  let cur = from;
  while (cur <= to) {
    out.push(cur);
    cur = addDays(cur, 1);
  }
  return out;
}

export function RosterPage() {
  const [from, setFrom] = useState(todayIso());
  const [to, setTo] = useState(addDays(todayIso(), 27));
  const [rows, setRows] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const list = await api<Assignment[]>(`/api/v1/roster?date_from=${from}&date_to=${to}`);
        if (!cancelled) setRows(list);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load roster");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [from, to]);

  const byDate = new Map<string, Assignment[]>();
  for (const r of rows) {
    const list = byDate.get(r.date_local) ?? [];
    list.push(r);
    byDate.set(r.date_local, list);
  }
  const days = dateRange(from, to);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>Roster calendar</CardTitle>
          <div className="flex items-center gap-2 text-sm text-dn-muted">
            <input
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              className="rounded-md border border-dn-steel-lt px-2 py-1 font-mono"
              data-testid="roster-date-from"
            />
            <span>→</span>
            <input
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="rounded-md border border-dn-steel-lt px-2 py-1 font-mono"
              data-testid="roster-date-to"
            />
          </div>
        </div>
      </CardHeader>
      <CardBody>
        {loading ? (
          <p className="text-sm text-dn-muted">Loading…</p>
        ) : error ? (
          <p className="text-sm text-dn-red">{error}</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-7 gap-2" data-testid="roster-calendar">
            {days.map((d) => {
              const dayAssignments = byDate.get(d) ?? [];
              return (
                <div
                  key={d}
                  className="rounded-md border border-dn-steel-lt p-2 min-h-[100px] bg-dn-fog"
                >
                  <div className="font-mono text-xs text-dn-steel mb-1">{d}</div>
                  {dayAssignments.length === 0 ? (
                    <div className="text-xs text-dn-muted">—</div>
                  ) : (
                    <ul className="space-y-1">
                      {dayAssignments.map((a) => (
                        <li
                          key={a.duty_day_key}
                          className="bg-white rounded border border-dn-steel-lt px-2 py-1 text-xs"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono">{a.aircraft_reg}</span>
                            <Badge tone="steel">{a.aircraft_type}</Badge>
                          </div>
                          <div className="text-dn-muted">
                            CAPT {a.captain_id} · FO {a.fo_id}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        )}
        {rows.length === 0 && !loading && !error && (
          <p className="mt-4 text-sm text-dn-muted" data-testid="roster-empty-hint">
            No published assignments in this window. Generate a roster via the optimiser API, then
            publish it to populate this calendar.
          </p>
        )}
      </CardBody>
    </Card>
  );
}
