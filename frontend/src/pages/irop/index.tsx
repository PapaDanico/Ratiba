import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { api, ApiError } from "@/lib/api";
import { AmendModal } from "@/components/roster/AmendModal";

type CrewLite = {
  id: string;
  employee_no: string;
  first_name: string;
  last_name: string;
  role: string;
};

type Cascade = {
  next_date: string | null;
  new_rest_h: number | null;
  rest_floor_h: number | null;
  breached: boolean;
  extension_h: number;
};

type Assessment = {
  crew_employee_no: string;
  date: string;
  away_from_base: boolean;
  original_flight_h: number;
  original_duty_h: number;
  original_legality: string;
  disrupted_flight_h: number;
  disrupted_duty_h: number;
  disrupted_legality: string;
  rules_breached: string[];
  cascade: Cascade;
  duty_day_key: string | null;
  aircraft_reg: string | null;
  captain_employee_no: string | null;
  fo_employee_no: string | null;
  crew_role_on_duty: string | null;
};

type AltCrew = {
  crew_id: string;
  employee_no: string;
  name: string;
  role: string;
  type_rated: boolean;
  landings_current: boolean;
  free: boolean;
  available: boolean;
};

const ROLE_OPTIONS = ["CAPT", "FO", "SO", "PURSER", "CABIN_CREW", "ENGINEER"];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function legalityTone(state: string): "green" | "amber" | "red" {
  if (state === "LEGAL") return "green";
  if (state === "ILLEGAL") return "red";
  return "amber";
}

function YesNo({ ok, yes, no }: { ok: boolean; yes: string; no: string }) {
  return <Badge tone={ok ? "green" : "red"}>{ok ? yes : no}</Badge>;
}

export function IropPage() {
  const [crew, setCrew] = useState<CrewLite[]>([]);

  // --- Disruption assessment form ---
  const [crewId, setCrewId] = useState("");
  const [date, setDate] = useState(todayIso());
  const [extraFlight, setExtraFlight] = useState("");
  const [extraGround, setExtraGround] = useState("");
  const [discretion, setDiscretion] = useState("");
  const [assessing, setAssessing] = useState(false);
  const [assessErr, setAssessErr] = useState<string | null>(null);
  const [result, setResult] = useState<Assessment | null>(null);

  // --- Relief-crew finder form ---
  const [reliefDate, setReliefDate] = useState(todayIso());
  const [role, setRole] = useState("CAPT");
  const [aircraftType, setAircraftType] = useState("");
  const [finding, setFinding] = useState(false);
  const [reliefErr, setReliefErr] = useState<string | null>(null);
  const [alts, setAlts] = useState<AltCrew[] | null>(null);

  // Relief hand-off: the assessed duty's amend context + the chosen candidate.
  const [amendFor, setAmendFor] = useState<AltCrew | null>(null);
  const [amended, setAmended] = useState<string | null>(null);

  // A candidate can relieve only when an assessed duty exposes an amend context,
  // the candidate fills the same seat as the disrupted crew member, and the
  // relief search was run for the same date as the assessed duty (otherwise the
  // candidate's availability was computed for a different day).
  function canRelieve(a: AltCrew): boolean {
    return (
      a.available &&
      !!result?.duty_day_key &&
      result.crew_role_on_duty === a.role &&
      (a.role === "CAPT" || a.role === "FO") &&
      reliefDate === result.date
    );
  }

  function amendPair(candidate: AltCrew): { captain: string; fo: string } {
    const cap = result?.captain_employee_no ?? "";
    const fo = result?.fo_employee_no ?? "";
    if (result?.crew_role_on_duty === "CAPT") return { captain: candidate.employee_no, fo };
    return { captain: cap, fo: candidate.employee_no };
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api<CrewLite[]>("/api/v1/crew");
        if (!cancelled) {
          const sorted = [...list].sort((a, b) => a.employee_no.localeCompare(b.employee_no));
          setCrew(sorted);
        }
      } catch {
        /* crew list is a convenience; the form still works with a pasted id */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function assess() {
    setAssessing(true);
    setAssessErr(null);
    setResult(null);
    try {
      const body = await api<Assessment>("/api/v1/irop/assess", {
        method: "POST",
        body: JSON.stringify({
          crew_id: crewId,
          date,
          extra_flight_h: Number(extraFlight || 0),
          extra_ground_h: Number(extraGround || 0),
          discretion_h: Number(discretion || 0),
        }),
      });
      setResult(body);
    } catch (err) {
      setAssessErr(
        err instanceof ApiError
          ? err.status === 404
            ? "No published flight duty for that crew member on that date."
            : err.message
          : "Assessment failed.",
      );
    } finally {
      setAssessing(false);
    }
  }

  async function findRelief() {
    setFinding(true);
    setReliefErr(null);
    setAlts(null);
    try {
      const rows = await api<AltCrew[]>("/api/v1/irop/alternatives", {
        method: "POST",
        body: JSON.stringify({
          date: reliefDate,
          role,
          aircraft_type: aircraftType.trim().toUpperCase(),
        }),
      });
      setAlts(rows);
    } catch (err) {
      setReliefErr(err instanceof ApiError ? err.message : "Lookup failed.");
    } finally {
      setFinding(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Disruption assessment</CardTitle>
        </CardHeader>
        <CardBody>
          <p className="text-sm text-dn-muted mb-4">
            Recompute a published duty&apos;s FTL legality when a diversion or delay adds block /
            ground time, and see whether it breaches limits and cascades into the next duty&apos;s
            rest. Read-only — it does not change the roster.
          </p>

          <div className="flex flex-wrap items-end gap-3 mb-4">
            <div className="min-w-[16rem]">
              <Label htmlFor="irop-crew">Crew</Label>
              <Select
                id="irop-crew"
                value={crewId}
                onChange={(e) => setCrewId(e.target.value)}
                data-testid="irop-crew-select"
              >
                <option value="">Select crew…</option>
                {crew.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.employee_no} — {c.first_name} {c.last_name} ({c.role})
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="irop-date">Date</Label>
              <Input
                id="irop-date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div className="w-32">
              <Label htmlFor="irop-flight">Extra flight (h)</Label>
              <Input
                id="irop-flight"
                type="number"
                min="0"
                max="12"
                step="0.1"
                value={extraFlight}
                onChange={(e) => setExtraFlight(e.target.value)}
              />
            </div>
            <div className="w-32">
              <Label htmlFor="irop-ground">Extra ground (h)</Label>
              <Input
                id="irop-ground"
                type="number"
                min="0"
                max="24"
                step="0.1"
                value={extraGround}
                onChange={(e) => setExtraGround(e.target.value)}
              />
            </div>
            <div className="w-32">
              <Label htmlFor="irop-disc">Discretion (h)</Label>
              <Input
                id="irop-disc"
                type="number"
                min="0"
                max="4"
                step="0.1"
                value={discretion}
                onChange={(e) => setDiscretion(e.target.value)}
              />
            </div>
            <Button size="sm" onClick={assess} disabled={!crewId || assessing}>
              {assessing ? "Assessing…" : "Assess"}
            </Button>
          </div>

          {assessErr && <ErrorAlert message={assessErr} />}

          {result && (
            <div className="rounded-md border border-dn-steel-lt p-4" data-testid="irop-result">
              <div className="flex flex-wrap items-center gap-3 mb-3">
                <span className="font-mono text-sm text-dn-dark">{result.crew_employee_no}</span>
                <span className="text-sm text-dn-muted">{result.date}</span>
                {result.away_from_base && <Badge tone="gold">Away from base</Badge>}
              </div>

              <div className="grid gap-4 sm:grid-cols-2 text-sm">
                <div>
                  <p className="text-dn-muted mb-1">Original</p>
                  <div className="flex items-center gap-2">
                    <Badge tone={legalityTone(result.original_legality)}>
                      {result.original_legality}
                    </Badge>
                    <span>
                      {result.original_flight_h}h flight · {result.original_duty_h}h duty
                    </span>
                  </div>
                </div>
                <div>
                  <p className="text-dn-muted mb-1">Disrupted</p>
                  <div className="flex items-center gap-2">
                    <Badge tone={legalityTone(result.disrupted_legality)}>
                      {result.disrupted_legality}
                    </Badge>
                    <span>
                      {result.disrupted_flight_h}h flight · {result.disrupted_duty_h}h duty
                    </span>
                  </div>
                </div>
              </div>

              {result.rules_breached.length > 0 && (
                <div className="mt-3">
                  <p className="text-dn-muted text-sm mb-1">Rules breached</p>
                  <div className="flex flex-wrap gap-1">
                    {result.rules_breached.map((r) => (
                      <Badge key={r} tone="red">
                        {r}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <div className="mt-3 border-t border-dn-steel-lt pt-3 text-sm">
                <p className="text-dn-muted mb-1">Cascade into next duty</p>
                {result.cascade.next_date == null ? (
                  <span className="text-dn-muted">No subsequent published duty.</span>
                ) : (
                  <div className="flex flex-wrap items-center gap-2">
                    <span>Next duty {result.cascade.next_date}:</span>
                    <span>
                      {result.cascade.new_rest_h}h rest vs {result.cascade.rest_floor_h}h floor
                    </span>
                    {result.cascade.extension_h > 0 && (
                      <span className="text-xs text-dn-muted">
                        (incl. +{result.cascade.extension_h}h per OPS033 §4.6.7)
                      </span>
                    )}
                    <YesNo ok={!result.cascade.breached} yes="Rest OK" no="Rest breached" />
                  </div>
                )}
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Find relief crew</CardTitle>
        </CardHeader>
        <CardBody>
          <p className="text-sm text-dn-muted mb-4">
            Crew who could legally cover a duty — same role, type-rated for the aircraft, 90-day
            landing-current and free that day. Available candidates are listed first.
          </p>

          <div className="flex flex-wrap items-end gap-3 mb-4">
            <div>
              <Label htmlFor="relief-date">Date</Label>
              <Input
                id="relief-date"
                type="date"
                value={reliefDate}
                onChange={(e) => setReliefDate(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="relief-role">Role</Label>
              <Select
                id="relief-role"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                data-testid="relief-role-select"
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </Select>
            </div>
            <div className="w-32">
              <Label htmlFor="relief-ac">Aircraft type</Label>
              <Input
                id="relief-ac"
                value={aircraftType}
                onChange={(e) => setAircraftType(e.target.value)}
                placeholder="e.g. DH8D"
              />
            </div>
            <Button size="sm" onClick={findRelief} disabled={!aircraftType.trim() || finding}>
              {finding ? "Searching…" : "Find relief"}
            </Button>
          </div>

          {reliefErr && <ErrorAlert message={reliefErr} />}
          {amended && (
            <div className="rounded border border-dn-green/30 bg-dn-green/5 px-3 py-2 text-sm text-dn-green-deep mb-4">
              {amended}
            </div>
          )}
          {alts && result?.duty_day_key && result.crew_role_on_duty && (
            <p className="text-xs text-dn-muted mb-2">
              Assessed duty <span className="font-mono">{result.duty_day_key}</span> — apply a
              relief {result.crew_role_on_duty} below to amend it (re-checks FTL &amp; logs the
              change).
            </p>
          )}

          {alts &&
            (alts.length === 0 ? (
              <p className="text-sm text-dn-muted">No crew of that role found.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm responsive-table">
                  <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                    <tr>
                      <th className="py-2 pr-4 font-medium">Crew</th>
                      <th className="py-2 pr-4 font-medium">Role</th>
                      <th className="py-2 pr-4 font-medium">Type-rated</th>
                      <th className="py-2 pr-4 font-medium">Landing-current</th>
                      <th className="py-2 pr-4 font-medium">Free</th>
                      <th className="py-2 pr-4 font-medium">Available</th>
                      <th className="py-2 pr-4 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-dn-steel-lt">
                    {alts.map((a) => (
                      <tr key={a.crew_id} className="hover:bg-dn-fog">
                        <td data-label="Crew" className="py-2 pr-4 text-dn-dark">
                          {a.name}{" "}
                          <span className="text-dn-muted font-mono text-xs">({a.employee_no})</span>
                        </td>
                        <td data-label="Role" className="py-2 pr-4">
                          {a.role}
                        </td>
                        <td data-label="Type-rated" className="py-2 pr-4">
                          <YesNo ok={a.type_rated} yes="Yes" no="No" />
                        </td>
                        <td data-label="Landing-current" className="py-2 pr-4">
                          <YesNo ok={a.landings_current} yes="Yes" no="No" />
                        </td>
                        <td data-label="Free" className="py-2 pr-4">
                          <YesNo ok={a.free} yes="Yes" no="No" />
                        </td>
                        <td data-label="Available" className="py-2 pr-4">
                          <YesNo ok={a.available} yes="Available" no="—" />
                        </td>
                        <td data-label="Action" className="py-2 pr-4">
                          {canRelieve(a) ? (
                            <button
                              type="button"
                              onClick={() => setAmendFor(a)}
                              className="text-dn-steel-deep underline text-xs hover:text-dn-dark"
                              data-testid={`apply-relief-${a.employee_no}`}
                            >
                              Apply relief
                            </button>
                          ) : (
                            <span className="text-dn-muted text-xs">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
        </CardBody>
      </Card>

      {amendFor && result?.duty_day_key && (
        <AmendModal
          dutyDayKey={result.duty_day_key}
          initialCaptain={amendPair(amendFor).captain}
          initialFo={amendPair(amendFor).fo}
          onClose={() => setAmendFor(null)}
          onAmended={() => {
            setAmended(
              `Duty ${result.duty_day_key} amended — ${amendFor.name} (${amendFor.employee_no}) assigned. FTL re-checked and change logged.`,
            );
            setAlts(null);
          }}
        />
      )}
    </div>
  );
}
