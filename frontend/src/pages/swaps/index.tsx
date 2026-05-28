import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { api, ApiError } from "@/lib/api";

type SwapRequest = {
  id: string;
  crew_id_initiator: string;
  crew_id_counterparty: string;
  fdp_or_sector_ref: string;
  reason: string | null;
  status: "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";
};

export function SwapsPage() {
  const [rows, setRows] = useState<SwapRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    try {
      const list = await api<SwapRequest[]>("/api/v1/swap?status=PENDING");
      setRows(list);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load swap requests");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function decide(id: string, status: "APPROVED" | "REJECTED") {
    setBusy(id);
    try {
      await api(`/api/v1/swap/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Decision failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pending swap requests</CardTitle>
      </CardHeader>
      <CardBody>
        {loading ? (
          <p className="text-sm text-dn-muted">Loading…</p>
        ) : error ? (
          <p className="text-sm text-dn-red">{error}</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-dn-muted" data-testid="no-pending-swap">
            No pending swap requests.
          </p>
        ) : (
          <ul className="divide-y divide-dn-steel-lt">
            {rows.map((r) => (
              <li
                key={r.id}
                className="py-3 flex flex-wrap items-center justify-between gap-3"
                data-testid="swap-row"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-mono text-xs text-dn-steel">
                    {r.crew_id_initiator.slice(0, 8)}… ↔ {r.crew_id_counterparty.slice(0, 8)}…
                  </div>
                  <div className="text-dn-dark">
                    <Badge tone="steel">{r.fdp_or_sector_ref}</Badge>
                  </div>
                  {r.reason && <div className="text-sm text-dn-muted mt-1">{r.reason}</div>}
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => decide(r.id, "REJECTED")}
                    disabled={busy === r.id}
                    data-testid={`reject-swap-${r.id}`}
                  >
                    Reject
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => decide(r.id, "APPROVED")}
                    disabled={busy === r.id}
                    data-testid={`approve-swap-${r.id}`}
                  >
                    Approve
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}
