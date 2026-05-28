import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { api, ApiError } from "@/lib/api";

type LeaveRequest = {
  id: string;
  crew_id: string;
  type: string;
  date_from: string;
  date_to: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  note: string | null;
};

export function LeavePage() {
  const [rows, setRows] = useState<LeaveRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    try {
      const list = await api<LeaveRequest[]>("/api/v1/leave?status=PENDING");
      setRows(list);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load leave requests");
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
      await api(`/api/v1/leave/${id}`, {
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
        <CardTitle>Pending leave requests</CardTitle>
      </CardHeader>
      <CardBody>
        {loading ? (
          <p className="text-sm text-dn-muted">Loading…</p>
        ) : error ? (
          <p className="text-sm text-dn-red">{error}</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-dn-muted" data-testid="no-pending-leave">
            No pending requests. Nicely done.
          </p>
        ) : (
          <ul className="divide-y divide-dn-steel-lt">
            {rows.map((r) => (
              <li
                key={r.id}
                className="py-3 flex flex-wrap items-center justify-between gap-3"
                data-testid="leave-row"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-mono text-xs text-dn-steel">{r.crew_id.slice(0, 8)}…</div>
                  <div className="text-dn-dark">
                    <Badge tone="steel">{r.type}</Badge>{" "}
                    <span className="font-mono">{r.date_from}</span> →{" "}
                    <span className="font-mono">{r.date_to}</span>
                  </div>
                  {r.note && <div className="text-sm text-dn-muted mt-1">{r.note}</div>}
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => decide(r.id, "REJECTED")}
                    disabled={busy === r.id}
                    data-testid={`reject-leave-${r.id}`}
                  >
                    Reject
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => decide(r.id, "APPROVED")}
                    disabled={busy === r.id}
                    data-testid={`approve-leave-${r.id}`}
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
