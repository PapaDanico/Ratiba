import { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api, ApiError } from "@/lib/api";

export type AmendModalProps = {
  dutyDayKey: string;
  initialCaptain: string;
  initialFo: string;
  onClose: () => void;
  onAmended: () => void;
};

/** Swap the (CAPT, FO) pair on a published duty day via /roster/amend.
 * The backend recomputes FTL legality and writes an AMEND_ROSTER audit event.
 * Employee numbers are entered/prefilled; reason is required for the audit. */
export function AmendModal({
  dutyDayKey,
  initialCaptain,
  initialFo,
  onClose,
  onAmended,
}: AmendModalProps) {
  const [captain, setCaptain] = useState(initialCaptain);
  const [fo, setFo] = useState(initialFo);
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
          duty_day_key: dutyDayKey,
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
    <Modal title={`Amend ${dutyDayKey}`} onClose={onClose} testId="amend-modal">
      <form onSubmit={onSubmit} className="space-y-3">
        <div>
          <Label htmlFor="amend-captain-input">Captain (employee #)</Label>
          <Input
            id="amend-captain-input"
            value={captain}
            onChange={(e) => setCaptain(e.target.value)}
            required
            data-testid="amend-captain"
          />
        </div>
        <div>
          <Label htmlFor="amend-fo-input">First Officer (employee #)</Label>
          <Input
            id="amend-fo-input"
            value={fo}
            onChange={(e) => setFo(e.target.value)}
            required
            data-testid="amend-fo"
          />
        </div>
        <div>
          <Label htmlFor="amend-reason-input">Reason (required for audit trail)</Label>
          <Input
            id="amend-reason-input"
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
    </Modal>
  );
}
