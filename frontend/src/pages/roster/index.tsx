import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api, ApiError } from "@/lib/api";

type Assignment = {
  duty_day_key: string;
  date_local: string;
  aircraft_reg: string;
  aircraft_type: string;
  sector_ids: string[];
  captain_id: string;
  fo_id: string;
  legality_state: "LEGAL" | "AT_LIMIT" | "REQUIRES_FRMS_DEROGATION" | "ILLEGAL" | null;
};

type PublicHoliday = {
  country_code: string;
  date: string;
  name: string;
  is_variable: boolean;
};

const COUNTRY_OPTIONS = [
  { code: "KE", label: "Kenya" },
  { code: "UG", label: "Uganda" },
  { code: "TZ", label: "Tanzania" },
  { code: "ET", label: "Ethiopia" },
];

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

function legalityTone(state: Assignment["legality_state"]): "green" | "amber" | "red" | "neutral" {
  if (state === "LEGAL") return "green";
  if (state === "AT_LIMIT") return "amber";
  if (state === "REQUIRES_FRMS_DEROGATION" || state === "ILLEGAL") return "red";
  return "neutral";
}

function AmendModal({
  assignment,
  onClose,
  onAmended,
}: {
  assignment: Assignment;
  onClose: () => void;
  onAmended: () => void;
}) {
  const [captain, setCaptain] = useState(assignment.captain_id);
  const [fo, setFo] = useState(assignment.fo_id);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/v1/roster/amend", {
        method: "POST",
        body: JSON.stringify({
          duty_day_key: assignment.duty_day_key,
          new_captain_employee_no: captain.trim(),
          new_fo_employee_no: fo.trim(),
          reason: reason.trim(),
        }),
      });
      onAmended();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Amend failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-dn-dark/40 p-4"
      role="dialog"
      aria-modal="true"
      data-testid="amend-modal"
    >
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Amend {assignment.duty_day_key}</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={onSubmit} className="space-y-3">
            <div>
              <Label htmlFor="captain">Captain (employee #)</Label>
              <Input
                id="captain"
                value={captain}
                onChange={(e) => setCaptain(e.target.value)}
                required
                data-testid="amend-captain"
              />
            </div>
            <div>
              <Label htmlFor="fo">First Officer (employee #)</Label>
              <Input
                id="fo"
                value={fo}
                onChange={(e) => setFo(e.target.value)}
                required
                data-testid="amend-fo"
              />
            </div>
            <div>
              <Label htmlFor="reason">Reason (required for audit trail)</Label>
              <Input
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                required
                minLength={1}
                data-testid="amend-reason"
              />
            </div>
            {error && <p className="text-sm text-dn-red">{error}</p>}
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="secondary" onClick={onClose} disabled={busy}>
                Cancel
              </Button>
              <Button type="submit" disabled={busy || !reason.trim()} data-testid="amend-submit">
                {busy ? "Saving…" : "Amend"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}

export function RosterPage() {
  const [from, setFrom] = useState(todayIso());
  const [to, setTo] = useState(addDays(todayIso(), 27));
  const [rows, setRows] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Assignment | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [holidayCountry, setHolidayCountry] = useState("KE");
  const [holidays, setHolidays] = useState<PublicHoliday[]>([]);

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
  }, [from, to, reloadKey]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api<PublicHoliday[]>(
          `/api/v1/reference/public-holidays?country_code=${holidayCountry}&date_from=${from}&date_to=${to}`,
        );
        if (!cancelled) setHolidays(list);
      } catch {
        if (!cancelled) setHolidays([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [holidayCountry, from, to]);

  const byDate = new Map<string, Assignment[]>();
  for (const r of rows) {
    const list = byDate.get(r.date_local) ?? [];
    list.push(r);
    byDate.set(r.date_local, list);
  }

  const holidayByDate = new Map<string, string>();
  for (const h of holidays) {
    holidayByDate.set(h.date, h.name);
  }

  const days = dateRange(from, to);

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>Roster calendar</CardTitle>
            <div className="flex flex-wrap items-center gap-3 text-sm text-dn-muted">
              {/* Date range */}
              <div className="flex items-center gap-2">
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
              {/* Holiday country picker */}
              <div className="flex items-center gap-1">
                <span className="text-xs text-dn-muted">Holidays:</span>
                <select
                  value={holidayCountry}
                  onChange={(e) => setHolidayCountry(e.target.value)}
                  className="rounded-md border border-dn-steel-lt px-2 py-1 text-xs font-mono"
                  data-testid="holiday-country-select"
                >
                  {COUNTRY_OPTIONS.map((c) => (
                    <option key={c.code} value={c.code}>{c.label}</option>
                  ))}
                </select>
              </div>
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
                const holidayName = holidayByDate.get(d);
                return (
                  <div
                    key={d}
                    className={[
                      "rounded-md border p-2 min-h-[100px]",
                      holidayName
                        ? "bg-amber-50 border-amber-200"
                        : "bg-dn-fog border-dn-steel-lt",
                    ].join(" ")}
                  >
                    <div className="font-mono text-xs text-dn-steel mb-1">{d}</div>
                    {holidayName && (
                      <div
                        className="text-xs font-medium text-amber-700 mb-1 truncate"
                        title={holidayName}
                      >
                        🏛 {holidayName}
                      </div>
                    )}
                    {dayAssignments.length === 0 ? (
                      <div className="text-xs text-dn-muted">—</div>
                    ) : (
                      <ul className="space-y-1">
                        {dayAssignments.map((a) => (
                          <li
                            key={a.duty_day_key}
                            className="bg-white rounded border border-dn-steel-lt px-2 py-1 text-xs"
                          >
                            <div className="flex items-center justify-between gap-1">
                              <span className="font-mono">{a.aircraft_reg}</span>
                              <Badge tone="steel">{a.aircraft_type}</Badge>
                            </div>
                            <div className="text-dn-muted truncate">
                              CAPT {a.captain_id} · FO {a.fo_id}
                            </div>
                            <div className="flex items-center justify-between mt-1">
                              {a.legality_state ? (
                                <Badge tone={legalityTone(a.legality_state)}>
                                  {a.legality_state}
                                </Badge>
                              ) : (
                                <span />
                              )}
                              <button
                                type="button"
                                onClick={() => setEditing(a)}
                                className="text-dn-steel underline text-xs"
                                data-testid={`amend-btn-${a.duty_day_key}`}
                              >
                                amend
                              </button>
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
      {editing && (
        <AmendModal
          assignment={editing}
          onClose={() => setEditing(null)}
          onAmended={() => setReloadKey((k) => k + 1)}
        />
      )}
    </>
  );
}
