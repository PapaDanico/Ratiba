import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api, ApiError } from "@/lib/api";

type Crew = {
  id: string;
  employee_no: string;
  first_name: string;
  last_name: string;
};

type AircraftType = { icao: string };

type TypeRating = {
  id: string;
  crew_id: string;
  employee_no: string;
  crew_name: string;
  aircraft_type: string;
  valid_from: string;
  valid_until: string;
  days_remaining: number;
  state: "GREEN" | "AMBER" | "RED";
};

type RecurrencyItem = {
  crew_id: string;
  employee_no: string;
  crew_name: string;
  kind: "currency" | "type_rating";
  label: string;
  expires_date: string;
  days_remaining: number;
  state: "GREEN" | "AMBER" | "RED";
};

function tone(state: "GREEN" | "AMBER" | "RED"): "green" | "amber" | "red" {
  return state === "GREEN" ? "green" : state === "AMBER" ? "amber" : "red";
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function addYears(iso: string, years: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCFullYear(d.getUTCFullYear() + years);
  return d.toISOString().slice(0, 10);
}

function RecurrencySection() {
  const [withinDays, setWithinDays] = useState(90);
  const [items, setItems] = useState<RecurrencyItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const list = await api<RecurrencyItem[]>(
          `/api/v1/training/recurrency?within_days=${withinDays}`,
        );
        if (!cancelled) setItems(list);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [withinDays]);

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle>Recurrency — expiring qualifications</CardTitle>
          <div className="flex items-center gap-2 text-sm text-dn-muted">
            <span>Within</span>
            <select
              value={withinDays}
              onChange={(e) => setWithinDays(Number(e.target.value))}
              className="rounded-md border border-dn-steel-lt px-2 py-1 text-sm"
              data-testid="recurrency-window"
            >
              <option value={30}>30 days</option>
              <option value={60}>60 days</option>
              <option value={90}>90 days</option>
              <option value={180}>180 days</option>
            </select>
          </div>
        </div>
      </CardHeader>
      <CardBody>
        {loading ? (
          <p className="text-sm text-dn-muted">Loading…</p>
        ) : error ? (
          <p className="text-sm text-dn-red">{error}</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-dn-muted" data-testid="recurrency-empty">
            Nothing expiring in this window. ✅
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm" data-testid="recurrency-table">
              <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                <tr>
                  <th className="py-2 pr-4 font-medium">Crew</th>
                  <th className="py-2 pr-4 font-medium">Item</th>
                  <th className="py-2 pr-4 font-medium">Expires</th>
                  <th className="py-2 pr-4 font-medium">Days left</th>
                  <th className="py-2 pr-4 font-medium">State</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dn-steel-lt">
                {items.map((i, idx) => (
                  <tr key={`${i.crew_id}-${i.label}-${idx}`} className="hover:bg-dn-fog">
                    <td className="py-2 pr-4">
                      <span className="text-dn-dark">{i.crew_name}</span>{" "}
                      <span className="font-mono text-xs text-dn-muted">({i.employee_no})</span>
                    </td>
                    <td className="py-2 pr-4">{i.label}</td>
                    <td className="py-2 pr-4 font-mono">{i.expires_date}</td>
                    <td className="py-2 pr-4 font-mono">{i.days_remaining}</td>
                    <td className="py-2 pr-4">
                      <Badge tone={tone(i.state)}>{i.state}</Badge>
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

function TypeRatingsSection() {
  const [ratings, setRatings] = useState<TypeRating[]>([]);
  const [crew, setCrew] = useState<Crew[]>([]);
  const [types, setTypes] = useState<AircraftType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // Add-form state
  const [crewId, setCrewId] = useState("");
  const [acType, setAcType] = useState("");
  const [validFrom, setValidFrom] = useState(todayIso());
  const [validUntil, setValidUntil] = useState(addYears(todayIso(), 1));
  const [busy, setBusy] = useState(false);
  const [formErr, setFormErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [c, t] = await Promise.all([
          api<Crew[]>("/api/v1/crew"),
          api<AircraftType[]>("/api/v1/reference/aircraft-types"),
        ]);
        if (!cancelled) {
          setCrew(c);
          setTypes(t);
          if (c[0]) setCrewId(c[0].id);
          if (t[0]) setAcType(t[0].icao);
        }
      } catch {
        /* non-fatal: form selects will be empty */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const list = await api<TypeRating[]>("/api/v1/training/type-ratings");
        if (!cancelled) setRatings(list);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  async function add(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setFormErr(null);
    try {
      await api(`/api/v1/training/crew/${crewId}/type-ratings`, {
        method: "POST",
        body: JSON.stringify({
          aircraft_type: acType,
          valid_from: validFrom,
          valid_until: validUntil,
        }),
      });
      setReloadKey((k) => k + 1);
    } catch (err) {
      setFormErr(err instanceof ApiError ? err.message : "Failed to add type rating");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    try {
      await api(`/api/v1/training/type-ratings/${id}`, { method: "DELETE" });
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Type ratings</CardTitle>
      </CardHeader>
      <CardBody>
        <p className="text-sm text-dn-muted mb-4">
          Type ratings qualify crew to operate an aircraft type — the auto-roster only assigns
          rated, current crew.
        </p>
        <form onSubmit={add} className="mb-6 space-y-3" data-testid="add-rating-form">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <Label htmlFor="tr-crew">Crew</Label>
              <select
                id="tr-crew"
                value={crewId}
                onChange={(e) => setCrewId(e.target.value)}
                className="w-full rounded-md border border-dn-steel-lt px-2 py-2 text-sm"
                required
              >
                {crew.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name} ({c.employee_no})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="tr-type">Aircraft type</Label>
              <select
                id="tr-type"
                value={acType}
                onChange={(e) => setAcType(e.target.value)}
                className="w-full rounded-md border border-dn-steel-lt px-2 py-2 text-sm"
                required
              >
                {types.map((t) => (
                  <option key={t.icao} value={t.icao}>
                    {t.icao}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="tr-from">Valid from</Label>
              <Input
                id="tr-from"
                type="date"
                value={validFrom}
                onChange={(e) => setValidFrom(e.target.value)}
                required
              />
            </div>
            <div>
              <Label htmlFor="tr-until">Valid until</Label>
              <Input
                id="tr-until"
                type="date"
                value={validUntil}
                onChange={(e) => setValidUntil(e.target.value)}
                required
              />
            </div>
          </div>
          {formErr && <p className="text-sm text-dn-red">{formErr}</p>}
          <div className="flex justify-end">
            <Button type="submit" disabled={busy || !crewId} data-testid="add-rating-submit">
              {busy ? "Adding…" : "Add type rating"}
            </Button>
          </div>
        </form>

        {loading ? (
          <p className="text-sm text-dn-muted">Loading…</p>
        ) : error ? (
          <p className="text-sm text-dn-red">{error}</p>
        ) : ratings.length === 0 ? (
          <p className="text-sm text-dn-muted" data-testid="ratings-empty">
            No type ratings recorded yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm" data-testid="ratings-table">
              <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                <tr>
                  <th className="py-2 pr-4 font-medium">Crew</th>
                  <th className="py-2 pr-4 font-medium">Type</th>
                  <th className="py-2 pr-4 font-medium">Valid from</th>
                  <th className="py-2 pr-4 font-medium">Valid until</th>
                  <th className="py-2 pr-4 font-medium">Days left</th>
                  <th className="py-2 pr-4 font-medium">State</th>
                  <th className="py-2 pr-4 font-medium" />
                </tr>
              </thead>
              <tbody className="divide-y divide-dn-steel-lt">
                {ratings.map((r) => (
                  <tr key={r.id} className="hover:bg-dn-fog">
                    <td className="py-2 pr-4">
                      <span className="text-dn-dark">{r.crew_name}</span>{" "}
                      <span className="font-mono text-xs text-dn-muted">({r.employee_no})</span>
                    </td>
                    <td className="py-2 pr-4">
                      <Badge tone="steel">{r.aircraft_type}</Badge>
                    </td>
                    <td className="py-2 pr-4 font-mono">{r.valid_from}</td>
                    <td className="py-2 pr-4 font-mono">{r.valid_until}</td>
                    <td className="py-2 pr-4 font-mono">{r.days_remaining}</td>
                    <td className="py-2 pr-4">
                      <Badge tone={tone(r.state)}>{r.state}</Badge>
                    </td>
                    <td className="py-2 pr-4">
                      <button
                        type="button"
                        onClick={() => remove(r.id)}
                        className="text-dn-red underline text-xs"
                        data-testid={`delete-rating-${r.id}`}
                      >
                        remove
                      </button>
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

export function TrainingPage() {
  return (
    <div className="space-y-6">
      <RecurrencySection />
      <TypeRatingsSection />
    </div>
  );
}
