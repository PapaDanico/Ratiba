import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Label } from "@/components/ui/Label";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { api, ApiError } from "@/lib/api";

type PostingCrew = {
  id: string;
  employee_no: string;
  first_name: string;
  last_name: string;
  role: string;
  crew_category: "FLIGHT_DECK" | "CABIN" | "ENGINEERING";
};

type Posting = {
  id: string;
  location_icao: string;
  country: string;
  base_tz: string;
  type: "ACMI_WET_LEASE" | "DETACHMENT" | "TRAINING";
  lessee_name: string | null;
  start_date: string;
  end_date: string;
  duration_days: number;
  notes: string | null;
  crew: PostingCrew[];
  engineer_cover: boolean;
  days_to_end: number;
  rotation_due: boolean;
};

type Crew = { id: string; employee_no: string; first_name: string; last_name: string };

const POSTING_TYPES: ReadonlyArray<readonly [Posting["type"], string]> = [
  ["ACMI_WET_LEASE", "ACMI wet-lease"],
  ["DETACHMENT", "Detachment"],
  ["TRAINING", "Training"],
];

const TYPE_LABEL: Record<Posting["type"], string> = {
  ACMI_WET_LEASE: "ACMI wet-lease",
  DETACHMENT: "Detachment",
  TRAINING: "Training",
};

const CAT_TONE: Record<PostingCrew["crew_category"], "steel" | "gold" | "amber"> = {
  FLIGHT_DECK: "steel",
  CABIN: "gold",
  ENGINEERING: "amber",
};

function AssignControl({
  postingId,
  crew,
  onDone,
}: {
  postingId: string;
  crew: Crew[];
  onDone: () => void;
}) {
  const [crewId, setCrewId] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // crew loads async in the parent; default the selection once it arrives.
  useEffect(() => {
    const first = crew[0];
    if (!crewId && first) setCrewId(first.id);
  }, [crew, crewId]);

  async function assign() {
    if (!crewId) return;
    setBusy(true);
    setErr(null);
    try {
      await api(`/api/v1/postings/${postingId}/assign`, {
        method: "POST",
        body: JSON.stringify({ crew_id: crewId }),
      });
      onDone();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Failed to assign");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-3 space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={crewId}
          onChange={(e) => setCrewId(e.target.value)}
          aria-label="Crew to assign"
          className="w-auto"
        >
          {crew.map((c) => (
            <option key={c.id} value={c.id}>
              {c.first_name} {c.last_name} ({c.employee_no})
            </option>
          ))}
        </Select>
        <Button size="sm" variant="secondary" onClick={assign} disabled={busy || !crewId}>
          {busy ? "Assigning…" : "Assign to posting"}
        </Button>
      </div>
      {err && <ErrorAlert message={err} />}
    </div>
  );
}

export function PostingsPage() {
  const [postings, setPostings] = useState<Posting[]>([]);
  const [crew, setCrew] = useState<Crew[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [icao, setIcao] = useState("");
  const [country, setCountry] = useState("");
  const [ptype, setPtype] = useState<Posting["type"]>("ACMI_WET_LEASE");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [lessee, setLessee] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [formErr, setFormErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const c = await api<Crew[]>("/api/v1/crew");
        if (!cancelled) setCrew(c);
      } catch {
        /* non-fatal */
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
        const list = await api<Posting[]>("/api/v1/postings");
        if (!cancelled) setPostings(list);
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

  async function create(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setFormErr(null);
    try {
      await api("/api/v1/postings", {
        method: "POST",
        body: JSON.stringify({
          location_icao: icao.trim().toUpperCase(),
          country: country.trim(),
          type: ptype,
          start_date: startDate,
          end_date: endDate,
          lessee_name: lessee.trim() || null,
          notes: notes.trim() || null,
        }),
      });
      setIcao("");
      setCountry("");
      setLessee("");
      setNotes("");
      setReloadKey((k) => k + 1);
    } catch (err) {
      setFormErr(err instanceof ApiError ? err.message : "Failed to create posting");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Outstation &amp; ACMI postings</CardTitle>
      </CardHeader>
      <CardBody>
        <p className="text-sm text-dn-muted mb-4">
          Deploy a crew team (flight deck + cabin + engineer) away from base for a bounded rotation.
          Rotations are capped at 28 days; international postings require each crew member to hold a
          valid work permit or visa.
        </p>

        <form onSubmit={create} className="mb-6 space-y-3" data-testid="create-posting-form">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div>
              <Label htmlFor="p-icao">Outstation (ICAO)</Label>
              <Input
                id="p-icao"
                value={icao}
                onChange={(e) => setIcao(e.target.value)}
                placeholder="HUEN"
                required
              />
            </div>
            <div>
              <Label htmlFor="p-country">Country</Label>
              <Input
                id="p-country"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                placeholder="Uganda"
                required
              />
            </div>
            <div>
              <Label htmlFor="p-type">Type</Label>
              <Select
                id="p-type"
                value={ptype}
                onChange={(e) => setPtype(e.target.value as Posting["type"])}
              >
                {POSTING_TYPES.map(([v, label]) => (
                  <option key={v} value={v}>
                    {label}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="p-start">Start</Label>
              <Input
                id="p-start"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
            </div>
            <div>
              <Label htmlFor="p-end">End</Label>
              <Input
                id="p-end"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
            </div>
            <div>
              <Label htmlFor="p-lessee">Lessee (optional)</Label>
              <Input id="p-lessee" value={lessee} onChange={(e) => setLessee(e.target.value)} />
            </div>
          </div>
          <div>
            <Label htmlFor="p-notes">Notes (optional)</Label>
            <Input id="p-notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
          </div>
          <div className="space-y-3">
            <Button type="submit" disabled={busy} data-testid="create-posting">
              {busy ? "Creating…" : "Create posting"}
            </Button>
            {formErr && <ErrorAlert message={formErr} />}
          </div>
        </form>

        {loading ? (
          <p className="text-sm text-dn-muted">Loading…</p>
        ) : error ? (
          <ErrorAlert message={error} />
        ) : postings.length === 0 ? (
          <p className="text-sm text-dn-muted">No postings yet. Create one above.</p>
        ) : (
          <div className="space-y-4" data-testid="postings-list">
            {postings.map((p) => (
              <div key={p.id} className="rounded-md border border-dn-steel-lt p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <span className="font-medium text-dn-dark">
                      {TYPE_LABEL[p.type]} · {p.location_icao}
                    </span>
                    <span className="text-dn-muted"> · {p.country}</span>
                    {p.lessee_name && <span className="text-dn-muted"> · {p.lessee_name}</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    {p.rotation_due && <Badge tone="red">Rotation due ({p.days_to_end}d)</Badge>}
                    {p.crew.length > 0 && !p.engineer_cover && (
                      <Badge tone="amber">No engineer cover</Badge>
                    )}
                    <Badge tone="steel">{p.duration_days} days</Badge>
                  </div>
                </div>
                <p className="mt-1 text-xs text-dn-muted">
                  {p.start_date} → {p.end_date}
                  {p.notes ? ` · ${p.notes}` : ""}
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {p.crew.length === 0 ? (
                    <span className="text-xs text-dn-muted">No crew assigned yet.</span>
                  ) : (
                    p.crew.map((m) => (
                      <Badge key={m.id} tone={CAT_TONE[m.crew_category]}>
                        {m.employee_no} · {m.role}
                      </Badge>
                    ))
                  )}
                </div>
                <AssignControl
                  postingId={p.id}
                  crew={crew}
                  onDone={() => setReloadKey((k) => k + 1)}
                />
              </div>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
}
