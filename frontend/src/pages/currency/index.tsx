import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { api, ApiError } from "@/lib/api";

type CurrencyStatus = {
  crew_id: string;
  currency_type: string;
  expires_date: string;
  days_remaining: number;
  state: "GREEN" | "AMBER" | "RED";
};

export function CurrencyPage() {
  const [rows, setRows] = useState<CurrencyStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api<CurrencyStatus[]>("/api/v1/crew/currency/dashboard");
        if (!cancelled) setRows(list);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load currency");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const toneFor = (state: CurrencyStatus["state"]) =>
    state === "GREEN" ? "green" : state === "AMBER" ? "amber" : "red";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Currency dashboard</CardTitle>
      </CardHeader>
      <CardBody>
        {loading ? (
          <TableSkeleton rows={6} cols={5} />
        ) : error ? (
          <p className="text-sm text-dn-red">{error}</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-dn-muted">No currencies recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm" data-testid="currency-table">
              <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                <tr>
                  <th className="py-2 pr-4 font-medium">Crew</th>
                  <th className="py-2 pr-4 font-medium">Currency</th>
                  <th className="py-2 pr-4 font-medium">Expires</th>
                  <th className="py-2 pr-4 font-medium">Days left</th>
                  <th className="py-2 pr-4 font-medium">State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dn-steel-lt">
                {rows.map((r, idx) => (
                  <tr key={`${r.crew_id}-${r.currency_type}-${idx}`} className="hover:bg-dn-fog">
                    <td className="py-2 pr-4 font-mono text-dn-steel">{r.crew_id.slice(0, 8)}…</td>
                    <td className="py-2 pr-4">{r.currency_type}</td>
                    <td className="py-2 pr-4 font-mono">{r.expires_date}</td>
                    <td className="py-2 pr-4 font-mono">{r.days_remaining}</td>
                    <td className="py-2 pr-4">
                      <Badge tone={toneFor(r.state)}>{r.state}</Badge>
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
