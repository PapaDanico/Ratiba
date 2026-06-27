import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { api, ApiError } from "@/lib/api";

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
  const [types, setTypes] = useState<AircraftType[]>([]);
  const [fleet, setFleet] = useState<Aircraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reg, setReg] = useState("");
  const [type, setType] = useState("");
  const [adding, setAdding] = useState(false);

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
              <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                <tr>
                  <th className="py-2 pr-4 font-medium">Registration</th>
                  <th className="py-2 pr-4 font-medium">Type</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dn-steel-lt">
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
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
