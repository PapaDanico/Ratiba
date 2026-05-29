import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api, ApiError } from "@/lib/api";

type FatigueRow = {
  employee_no: string;
  name: string;
  role: string;
  fdp_count: number;
  night_fdp_count: number;
  night_pct: number;
  max_consecutive_days: number;
  elevated_count: number;
  high_count: number;
  peak_score: number;
  peak_band: "LOW" | "ELEVATED" | "HIGH";
};

const BAND_TONE: Record<FatigueRow["peak_band"], "green" | "amber" | "red"> = {
  LOW: "green",
  ELEVATED: "amber",
  HIGH: "red",
};

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

export function FatiguePage() {
  const [from, setFrom] = useState(isoDaysAgo(28));
  const [to, setTo] = useState(isoDaysAgo(0));
  const [rows, setRows] = useState<FatigueRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const data = await api<FatigueRow[]>(
          `/api/v1/reports/fatigue?date_from=${from}&date_to=${to}`,
        );
        if (!cancelled) setRows(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey, from, to]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Fatigue screen</CardTitle>
      </CardHeader>
      <CardBody>
        <p className="text-sm text-dn-muted mb-4">
          An advisory, FRMS-aligned fatigue screen (per ICAO Doc 9966 principles) — it flags duties
          likely to carry elevated fatigue from circadian timing, duty length, sectors, short rest
          and consecutive-duty streaks. It is <strong>not</strong> a legal verdict (the FTL limits
          remain the gate) and <strong>not</strong> a validated biomathematical model.
        </p>

        <div className="mb-4 flex flex-wrap items-end gap-3">
          <div>
            <Label htmlFor="f-from">From</Label>
            <Input id="f-from" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          </div>
          <div>
            <Label htmlFor="f-to">To</Label>
            <Input id="f-to" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          </div>
          <Button variant="secondary" size="sm" onClick={() => setReloadKey((k) => k + 1)}>
            Refresh
          </Button>
        </div>

        {loading ? (
          <p className="text-sm text-dn-muted">Loading…</p>
        ) : error ? (
          <p className="text-sm text-dn-red">{error}</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-dn-muted">No duties in this period.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm responsive-table">
              <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                <tr>
                  <th className="py-2 pr-4 font-medium">Crew</th>
                  <th className="py-2 pr-4 font-medium">Role</th>
                  <th className="py-2 pr-4 font-medium">FDPs</th>
                  <th className="py-2 pr-4 font-medium">Night %</th>
                  <th className="py-2 pr-4 font-medium">Max consec. days</th>
                  <th className="py-2 pr-4 font-medium">Elevated / High</th>
                  <th className="py-2 pr-4 font-medium">Peak</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dn-steel-lt">
                {rows.map((r) => (
                  <tr key={r.employee_no} className="hover:bg-dn-fog">
                    <td data-label="Crew" className="py-2 pr-4 text-dn-dark">
                      {r.name}{" "}
                      <span className="text-dn-muted font-mono text-xs">({r.employee_no})</span>
                    </td>
                    <td data-label="Role" className="py-2 pr-4">
                      {r.role}
                    </td>
                    <td data-label="FDPs" className="py-2 pr-4">
                      {r.fdp_count}
                    </td>
                    <td data-label="Night %" className="py-2 pr-4">
                      {r.night_pct > 25 ? (
                        <Badge tone="amber">{r.night_pct}%</Badge>
                      ) : (
                        `${r.night_pct}%`
                      )}
                    </td>
                    <td data-label="Max consec. days" className="py-2 pr-4">
                      {r.max_consecutive_days > 6 ? (
                        <Badge tone="red">{r.max_consecutive_days}</Badge>
                      ) : (
                        r.max_consecutive_days
                      )}
                    </td>
                    <td data-label="Elevated / High" className="py-2 pr-4">
                      {r.elevated_count} / {r.high_count}
                    </td>
                    <td data-label="Peak" className="py-2 pr-4">
                      <Badge tone={BAND_TONE[r.peak_band]}>
                        {r.peak_score} · {r.peak_band}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
