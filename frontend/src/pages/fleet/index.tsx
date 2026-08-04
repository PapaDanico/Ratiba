import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { Modal } from "@/components/ui/Modal";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/lib/toast";

type AircraftType = {
  icao: string;
  manufacturer: string;
  model: string;
  category: string;
  typical_seats: number;
  label: string;
};

type Aircraft = {
  id: string;
  registration: string;
  aircraft_type: string;
  active: boolean;
  aircraft_type_known: boolean;
};

const CATEGORY_LABEL: Record<string, string> = {
  turboprop: "Turboprops",
  light: "Light / utility",
  regional_jet: "Regional jets",
  narrowbody: "Narrowbody",
};

export function FleetPage() {
  const toast = useToast();
  const [types, setTypes] = useState<AircraftType[]>([]);
  const [fleet, setFleet] = useState<Aircraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reg, setReg] = useState("");
  const [type, setType] = useState("");
  const [adding, setAdding] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [deleteModal, setDeleteModal] = useState<Aircraft | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteErr, setDeleteErr] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    try {
      const [t, f] = await Promise.all([
        api<AircraftType[]>("/api/v1/reference/aircraft-types"),
        api<Aircraft[]>("/api/v1/fleet"),
      ]);
      setTypes(t);
      setFleet(f);
      if (!type && t.length) setType(t[0]!.icao);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load fleet");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setAdding(true);
    setError(null);
    try {
      await api("/api/v1/fleet", {
        method: "POST",
        body: JSON.stringify({
          registration: reg.trim().toUpperCase(),
          aircraft_type: type,
          active: true,
        }),
      });
      setReg("");
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Add failed");
    } finally {
      setAdding(false);
    }
  }

  async function toggleActive(a: Aircraft) {
    setBusyId(a.id);
    setError(null);
    try {
      await api(`/api/v1/fleet/${a.id}`, {
        method: "PATCH",
        body: JSON.stringify({ active: !a.active }),
      });
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Update failed");
    } finally {
      setBusyId(null);
    }
  }

  async function confirmDelete() {
    if (!deleteModal) return;
    const a = deleteModal;
    setDeleting(true);
    setDeleteErr(null);
    try {
      await api(`/api/v1/fleet/${a.id}`, { method: "DELETE" });
      setDeleteModal(null);
      await reload();
      // Undo re-registers the aircraft (deletes are only allowed for
      // aircraft with no sectors, so a fresh POST restores it faithfully).
      toast.show(`${a.registration} removed from fleet`, "info", {
        label: "Undo",
        onClick: async () => {
          try {
            await api("/api/v1/fleet", {
              method: "POST",
              body: JSON.stringify({
                registration: a.registration,
                aircraft_type: a.aircraft_type,
              }),
            });
            await reload();
            toast.show(`${a.registration} restored`, "success");
          } catch {
            toast.show("Could not restore the aircraft", "error");
          }
        },
      });
    } catch (err) {
      setDeleteErr(err instanceof ApiError ? err.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  }

  // Group reference types by category for the dropdown's optgroups.
  const byCategory = new Map<string, AircraftType[]>();
  for (const t of types) {
    const list = byCategory.get(t.category) ?? [];
    list.push(t);
    byCategory.set(t.category, list);
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Add aircraft to your fleet</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={add} className="flex flex-wrap items-end gap-3">
            <div>
              <Label htmlFor="reg">Registration</Label>
              <Input
                id="reg"
                value={reg}
                onChange={(e) => setReg(e.target.value.toUpperCase())}
                placeholder="5Y-ABC"
                required
                className="w-40"
                data-testid="fleet-registration"
              />
            </div>
            <div>
              <Label htmlFor="type">Aircraft type</Label>
              <Select
                id="type"
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="min-w-[20rem]"
                data-testid="fleet-type"
              >
                {[...byCategory.entries()].map(([cat, list]) => (
                  <optgroup key={cat} label={CATEGORY_LABEL[cat] ?? cat}>
                    {list.map((t) => (
                      <option key={t.icao} value={t.icao}>
                        {t.label} · {t.typical_seats} seats
                      </option>
                    ))}
                  </optgroup>
                ))}
              </Select>
            </div>
            <Button type="submit" disabled={adding} data-testid="fleet-add">
              {adding ? "Adding…" : "Add aircraft"}
            </Button>
          </form>
          {error && <ErrorAlert message={error} className="mt-3" />}
          <p className="mt-3 text-xs text-dn-muted">
            The list covers the types common to sub-scale East &amp; Central African operators —
            turboprops, light utility, regional jets, and smaller narrowbodies. Don&apos;t see
            yours? Tell us and we&apos;ll add it.
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Fleet</CardTitle>
        </CardHeader>
        <CardBody>
          {loading ? (
            <TableSkeleton rows={5} cols={3} />
          ) : fleet.length === 0 ? (
            <p className="text-sm text-dn-muted" data-testid="no-fleet">
              No aircraft registered yet.
            </p>
          ) : (
            <table className="min-w-full text-sm" data-testid="fleet-table">
              <thead className="text-left text-dn-muted border-b border-dn-navy-lt">
                <tr>
                  <th className="py-2 pr-4 font-medium">Registration</th>
                  <th className="py-2 pr-4 font-medium">Type</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                  <th className="py-2 pr-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dn-navy-lt">
                {fleet.map((a) => (
                  <tr key={a.id} className="hover:bg-dn-fog">
                    <td className="py-2 pr-4 font-mono">{a.registration}</td>
                    <td className="py-2 pr-4">
                      <span className="font-mono">{a.aircraft_type}</span>
                      {!a.aircraft_type_known && (
                        <span className="ml-2 text-xs text-dn-amber">(custom)</span>
                      )}
                    </td>
                    <td className="py-2 pr-4">
                      {a.active ? (
                        <Badge tone="green">Active</Badge>
                      ) : (
                        <Badge tone="neutral">Inactive</Badge>
                      )}
                    </td>
                    <td className="py-2 pr-4">
                      <div className="flex items-center gap-3">
                        <button
                          type="button"
                          onClick={() => void toggleActive(a)}
                          disabled={busyId === a.id}
                          className="text-dn-navy-deep underline text-xs disabled:opacity-50"
                          data-testid={`fleet-toggle-${a.id}`}
                        >
                          {busyId === a.id ? "…" : a.active ? "deactivate" : "activate"}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setDeleteErr(null);
                            setDeleteModal(a);
                          }}
                          className="text-dn-red underline text-xs"
                          data-testid={`fleet-delete-${a.id}`}
                        >
                          delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>

      {deleteModal && (
        <Modal
          title="Delete aircraft"
          onClose={() => setDeleteModal(null)}
          disableEscape={deleting}
        >
          <div className="space-y-4">
            <p className="text-sm text-dn-dark">
              Delete {deleteModal.registration} from the fleet? You can undo for a few seconds
              afterwards. Aircraft with recorded flight sectors can&apos;t be deleted — deactivate
              them instead.
            </p>
            {deleteErr && <ErrorAlert message={deleteErr} />}
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setDeleteModal(null)} disabled={deleting}>
                Cancel
              </Button>
              <Button variant="danger" onClick={confirmDelete} disabled={deleting}>
                {deleting ? "Deleting…" : "Delete"}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
