import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/lib/toast";

type LeaveRequest = {
  id: string;
  crew_id: string;
  type: string;
  date_from: string;
  date_to: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  note: string | null;
};

type CrewLite = { id: string; employee_no: string; first_name: string; last_name: string };

export function LeavePage() {
  const toast = useToast();
  const [rows, setRows] = useState<LeaveRequest[]>([]);
  const [crewById, setCrewById] = useState<Record<string, CrewLite>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  // Confirmation modal state
  const [confirmModal, setConfirmModal] = useState<{
    id: string;
    status: "APPROVED" | "REJECTED";
    request: LeaveRequest;
  } | null>(null);

  function crewLabel(crewId: string): string {
    const c = crewById[crewId];
    return c ? `${c.first_name} ${c.last_name} (${c.employee_no})` : `${crewId.slice(0, 8)}…`;
  }

  async function reload() {
    setLoading(true);
    try {
      const [list, crew] = await Promise.all([
        api<LeaveRequest[]>("/api/v1/leave?status=PENDING"),
        api<CrewLite[]>("/api/v1/crew"),
      ]);
      setRows(list);
      setCrewById(Object.fromEntries(crew.map((c) => [c.id, c])));
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

  async function confirmDecision() {
    if (!confirmModal) return;
    setBusy(confirmModal.id);
    try {
      await api(`/api/v1/leave/${confirmModal.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: confirmModal.status }),
      });
      await reload();
      toast.show(`Leave ${confirmModal.status.toLowerCase()}`, "success");
      setConfirmModal(null);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Decision failed";
      setError(msg);
      toast.show(msg, "error");
    } finally {
      setBusy(null);
    }
  }

  function showConfirm(request: LeaveRequest, status: "APPROVED" | "REJECTED") {
    setConfirmModal({ id: request.id, status, request });
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
          <ErrorAlert message={error} />
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
                  <div className="text-sm font-medium text-dn-steel-deep">
                    {crewLabel(r.crew_id)}
                  </div>
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
                    onClick={() => showConfirm(r, "REJECTED")}
                    disabled={busy === r.id}
                    data-testid={`reject-leave-${r.id}`}
                  >
                    Reject
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => showConfirm(r, "APPROVED")}
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

        {confirmModal && (
          <Modal
            title={`${confirmModal.status === "APPROVED" ? "Approve" : "Reject"} leave request`}
            onClose={() => setConfirmModal(null)}
            disableEscape={busy === confirmModal.id}
          >
            <div className="space-y-4">
              <div className="bg-dn-fog rounded p-3 space-y-2">
                <div>
                  <span className="text-xs text-dn-muted">Crew</span>
                  <div className="font-medium">{crewLabel(confirmModal.request.crew_id)}</div>
                </div>
                <div>
                  <span className="text-xs text-dn-muted">Type</span>
                  <div className="font-medium">{confirmModal.request.type}</div>
                </div>
                <div>
                  <span className="text-xs text-dn-muted">Dates</span>
                  <div className="font-mono">
                    {confirmModal.request.date_from} → {confirmModal.request.date_to}
                  </div>
                </div>
                {confirmModal.request.note && (
                  <div>
                    <span className="text-xs text-dn-muted">Note</span>
                    <div className="text-sm">{confirmModal.request.note}</div>
                  </div>
                )}
              </div>
              <p className="text-sm text-dn-dark">
                {confirmModal.status === "APPROVED"
                  ? "Approve this leave request?"
                  : "Reject this leave request?"}
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
