import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/lib/toast";

type SwapRequest = {
  id: string;
  crew_id_initiator: string;
  crew_id_counterparty: string;
  fdp_or_sector_ref: string;
  reason: string | null;
  status: "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";
};

export function SwapsPage() {
  const toast = useToast();
  const [rows, setRows] = useState<SwapRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  // Confirmation modal state
  const [confirmModal, setConfirmModal] = useState<{
    id: string;
    status: "APPROVED" | "REJECTED";
    request: SwapRequest;
  } | null>(null);

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

  async function confirmDecision() {
    if (!confirmModal) return;
    setBusy(confirmModal.id);
    try {
      await api(`/api/v1/swap/${confirmModal.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: confirmModal.status }),
      });
      await reload();
      toast.show(`Swap ${confirmModal.status.toLowerCase()}`, "success");
      setConfirmModal(null);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Decision failed";
      setError(msg);
      toast.show(msg, "error");
    } finally {
      setBusy(null);
    }
  }

  function showConfirm(request: SwapRequest, status: "APPROVED" | "REJECTED") {
    setConfirmModal({ id: request.id, status, request });
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
          <ErrorAlert message={error} />
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
                  <div className="font-mono text-xs text-dn-steel-deep">
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
                    onClick={() => showConfirm(r, "REJECTED")}
                    disabled={busy === r.id}
                    data-testid={`reject-swap-${r.id}`}
                  >
                    Reject
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => showConfirm(r, "APPROVED")}
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

        {confirmModal && (
          <Modal
            title={`${confirmModal.status === "APPROVED" ? "Approve" : "Reject"} swap request`}
            onClose={() => setConfirmModal(null)}
            disableEscape={busy === confirmModal.id}
          >
            <div className="space-y-4">
              <div className="bg-dn-fog rounded p-3 space-y-2">
                <div>
                  <span className="text-xs text-dn-muted">Crew swap</span>
                  <div className="font-mono text-sm">
                    {confirmModal.request.crew_id_initiator.slice(0, 8)}… ↔{" "}
                    {confirmModal.request.crew_id_counterparty.slice(0, 8)}…
                  </div>
                </div>
                <div>
                  <span className="text-xs text-dn-muted">Flight/FDP</span>
                  <div className="font-medium">{confirmModal.request.fdp_or_sector_ref}</div>
                </div>
                {confirmModal.request.reason && (
                  <div>
                    <span className="text-xs text-dn-muted">Reason</span>
                    <div className="text-sm">{confirmModal.request.reason}</div>
                  </div>
                )}
              </div>
              <p className="text-sm text-dn-dark">
                {confirmModal.status === "APPROVED"
                  ? "Approve this swap request?"
                  : "Reject this swap request?"}
              </p>
              <div className="flex justify-end gap-3">
                <Button
                  variant="secondary"
                  onClick={() => setConfirmModal(null)}
                  disabled={busy === confirmModal.id}
                >
                  Cancel
                </Button>
                <Button
                  variant={confirmModal.status === "APPROVED" ? "primary" : "secondary"}
                  onClick={confirmDecision}
                  disabled={busy === confirmModal.id}
                >
                  {busy === confirmModal.id
                    ? "Processing…"
                    : confirmModal.status === "APPROVED"
                      ? "Approve"
                      : "Reject"}
                </Button>
              </div>
            </div>
          </Modal>
        )}
      </CardBody>
    </Card>
  );
}
