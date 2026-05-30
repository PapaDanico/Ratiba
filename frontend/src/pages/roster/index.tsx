import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { AmendModal } from "@/components/roster/AmendModal";

type AmendResponse = {
  duty_day_key: string;
  captain_id: string;
  fo_id: string;
  legality_state: Assignment["legality_state"];
};

type CrewFull = {
  id: string;
  employee_no: string;
  first_name: string;
  last_name: string;
  role: "CAPT" | "FO" | "SO" | "PURSER" | "CABIN_CREW" | "ENGINEER";
  crew_category: "FLIGHT_DECK" | "CABIN" | "ENGINEERING";
  active: boolean;
};

type Assignment = {
  duty_day_key: string;
  date_local: string;
  aircraft_reg: string;
  aircraft_type: string;
  sector_ids: string[];
  captain_id: string;
  fo_id: string;
  legality_state: "LEGAL" | "AT_LIMIT" | "REQUIRES_FRMS_DEROGATION" | "ILLEGAL" | null;
};

type PublicHoliday = {
  country_code: string;
  date: string;
  name: string;
  is_variable: boolean;
};

type SectorInput = {
  sector_id: string;
  date_local: string;
  std: string;
  sta: string;
  aircraft_reg: string;
  aircraft_type: string;
  block_hours: number;
};

type RosterResult = {
  status: string;
  assignments: Assignment[];
  objective_value: number | null;
  unassigned_duty_days: string[];
  diagnostics: Record<string, unknown>;
  elapsed_s: number;
};

type AutoGenerateResponse = {
  result: RosterResult;
  sectors: SectorInput[];
};

type Draft = {
  result: RosterResult;
  sectors: SectorInput[];
};

const COUNTRY_OPTIONS = [
  { code: "KE", label: "Kenya" },
  { code: "UG", label: "Uganda" },
  { code: "TZ", label: "Tanzania" },
  { code: "ET", label: "Ethiopia" },
  { code: "SO", label: "Somalia" },
  { code: "SS", label: "South Sudan" },
];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function addDays(iso: string, days: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function dateRange(from: string, to: string): string[] {
  const out: string[] = [];
  let cur = from;
  while (cur <= to) {
    out.push(cur);
    cur = addDays(cur, 1);
  }
  return out;
}

function legalityTone(state: Assignment["legality_state"]): "green" | "amber" | "red" | "neutral" {
  if (state === "LEGAL") return "green";
  if (state === "AT_LIMIT") return "amber";
  if (state === "REQUIRES_FRMS_DEROGATION" || state === "ILLEGAL") return "red";
  return "neutral";
}

type CrewLite = { id: string; employee_no: string; first_name: string; last_name: string };

type Duty = {
  id: string;
  crew_id: string;
  employee_no: string;
  crew_name: string;
  date: string;
  type: string;
  start: string;
  end: string;
  duration_h: number;
  legality_state: "LEGAL" | "AT_LIMIT" | "REQUIRES_FRMS_DEROGATION" | "ILLEGAL" | null;
};

function StandbyPanel({ from, to }: { from: string; to: string }) {
  const [crew, setCrew] = useState<CrewLite[]>([]);
  const [duties, setDuties] = useState<Duty[]>([]);
  const [reloadKey, setReloadKey] = useState(0);
  const [crewId, setCrewId] = useState("");
  const [dutyType, setDutyType] = useState("STANDBY_SHORT");
  const [day, setDay] = useState(from);
  const [start, setStart] = useState("06:00");
  const [end, setEnd] = useState("14:00");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api<CrewLite[]>("/api/v1/crew");
        if (!cancelled) {
          setCrew(list);
          if (list[0]) setCrewId(list[0].id);
        }
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
    (async () => {
      try {
        const list = await api<Duty[]>(`/api/v1/duties?date_from=${from}&date_to=${to}`);
        if (!cancelled) setDuties(list);
      } catch {
        if (!cancelled) setDuties([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [from, to, reloadKey]);

  const isStandby = dutyType !== "OFF";

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/v1/duties", {
        method: "POST",
        body: JSON.stringify({
          crew_id: crewId,
          date: day,
          duty_type: dutyType,
          start_time: isStandby ? start : null,
          end_time: isStandby ? end : null,
        }),
      });
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to assign duty");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    try {
      await api(`/api/v1/duties/${id}`, { method: "DELETE" });
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete duty");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Standby &amp; days off</CardTitle>
      </CardHeader>
      <CardBody>
        <form onSubmit={submit} className="mb-5 space-y-3" data-testid="assign-duty-form">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <div>
              <Label htmlFor="d-crew">Crew</Label>
              <select
                id="d-crew"
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
              <Label htmlFor="d-type">Duty</Label>
              <select
                id="d-type"
                value={dutyType}
                onChange={(e) => setDutyType(e.target.value)}
                className="w-full rounded-md border border-dn-steel-lt px-2 py-2 text-sm"
              >
                <option value="STANDBY_SHORT">Standby (short-call)</option>
                <option value="STANDBY_LONG">Standby (long-call)</option>
                <option value="OFF">Day off</option>
              </select>
            </div>
            <div>
              <Label htmlFor="d-date">Date</Label>
              <Input
                id="d-date"
                type="date"
                value={day}
                onChange={(e) => setDay(e.target.value)}
                required
              />
            </div>
            {isStandby && (
              <>
                <div>
                  <Label htmlFor="d-start">Start (UTC)</Label>
                  <Input
                    id="d-start"
                    type="time"
                    value={start}
                    onChange={(e) => setStart(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="d-end">End (UTC)</Label>
                  <Input
                    id="d-end"
                    type="time"
                    value={end}
                    onChange={(e) => setEnd(e.target.value)}
                    required
                  />
                </div>
              </>
            )}
          </div>
          {error && <p className="text-sm text-dn-red">{error}</p>}
          <div className="flex justify-end">
            <Button type="submit" disabled={busy || !crewId} data-testid="assign-duty-submit">
              {busy ? "Assigning…" : "Assign duty"}
            </Button>
          </div>
        </form>

        {duties.length === 0 ? (
          <p className="text-sm text-dn-muted" data-testid="duties-empty">
            No standby or off-day duties in this window.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="rtable min-w-full text-sm" data-testid="duties-table">
              <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                <tr>
                  <th className="py-3 pr-4 font-medium">Crew</th>
                  <th className="py-3 pr-4 font-medium">Date</th>
                  <th className="py-3 pr-4 font-medium">Type</th>
                  <th className="py-3 pr-4 font-medium">Window (UTC)</th>
                  <th className="py-3 pr-4 font-medium">State</th>
                  <th className="py-3 pr-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dn-steel-lt">
                {duties.map((d) => (
                  <tr key={d.id}>
                    <td data-label="Crew" className="py-3 pr-4">
                      <span className="text-dn-dark">{d.crew_name}</span>{" "}
                      <span className="font-mono text-xs text-dn-muted">({d.employee_no})</span>
                    </td>
                    <td data-label="Date" className="py-3 pr-4 font-mono">
                      {d.date}
                    </td>
                    <td data-label="Type" className="py-3 pr-4">
                      <Badge tone={d.type === "STANDBY" ? "amber" : "neutral"}>{d.type}</Badge>
                    </td>
                    <td data-label="Window (UTC)" className="py-3 pr-4 font-mono text-xs">
                      {d.type === "OFF" ? "—" : `${d.duration_h.toFixed(1)}h`}
                    </td>
                    <td data-label="State" className="py-3 pr-4">
                      {d.legality_state ? (
                        <Badge tone={legalityTone(d.legality_state)}>{d.legality_state}</Badge>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td data-label="" className="py-3 pr-4">
                      <div className="row-actions flex justify-end">
                        <button
                          type="button"
                          onClick={() => remove(d.id)}
                          className="text-dn-red underline text-xs"
                          data-testid={`delete-duty-${d.id}`}
                        >
                          remove
                        </button>
                      </div>
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

export function RosterPage() {
  const [from, setFrom] = useState(todayIso());
  const [to, setTo] = useState(addDays(todayIso(), 27));
  const [rows, setRows] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Assignment | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [holidayCountry, setHolidayCountry] = useState("KE");
  const [holidays, setHolidays] = useState<PublicHoliday[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [generating, setGenerating] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [draftMsg, setDraftMsg] = useState<string | null>(null);
  const [crew, setCrew] = useState<CrewFull[]>([]);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [dragOverZone, setDragOverZone] = useState<string | null>(null);
  const [draggingRole, setDraggingRole] = useState<"CAPT" | "FO" | null>(null);
  const toast = useToast();

  // A captain may operate either seat; an FO may only fill the FO seat.
  function roleFits(crewRole: string | undefined, slot: "CAPT" | "FO"): boolean {
    if (crewRole === "CAPT") return true;
    return slot === "FO" && crewRole === "FO";
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api<CrewFull[]>("/api/v1/crew");
        if (!cancelled) setCrew(list);
      } catch {
        if (!cancelled) setCrew([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  // NOTE: the roster list contract puts crew *employee numbers* in
  // `captain_id`/`fo_id` (not UUIDs), so keys here are employee numbers.
  const crewByEmpNo = new Map(crew.map((c) => [c.employee_no, c]));

  function crewLabel(empNo: string): string {
    const c = crewByEmpNo.get(empNo);
    return c ? `${empNo} · ${c.first_name} ${c.last_name}` : empNo;
  }

  /** Reassign a duty's CAPT/FO via drag-and-drop: optimistic swap, then
   * /roster/amend recomputes FTL legality (reconciled or rolled back). */
  async function reassign(a: Assignment, role: "CAPT" | "FO", newEmpNo: string) {
    const currentEmp = role === "CAPT" ? a.captain_id : a.fo_id;
    if (newEmpNo === currentEmp) return; // dropped onto the same crew
    const newRole = crewByEmpNo.get(newEmpNo)?.role;
    if (!roleFits(newRole, role)) {
      // Don't burn a request the backend will reject — explain instead.
      toast.show(`${newEmpNo} (${newRole ?? "?"}) isn't rated for the ${role} seat`, "error");
      return;
    }
    const newCaptainEmp = role === "CAPT" ? newEmpNo : a.captain_id;
    const newFoEmp = role === "FO" ? newEmpNo : a.fo_id;

    const prevRows = rows;
    setSavingKey(a.duty_day_key);
    setRows((rs) =>
      rs.map((r) =>
        r.duty_day_key === a.duty_day_key
          ? { ...r, captain_id: newCaptainEmp, fo_id: newFoEmp, legality_state: null }
          : r,
      ),
    );
    try {
      const res = await api<AmendResponse>("/api/v1/roster/amend", {
        method: "POST",
        body: JSON.stringify({
          duty_day_key: a.duty_day_key,
          new_captain_employee_no: newCaptainEmp,
          new_fo_employee_no: newFoEmp,
          reason: "Drag-and-drop crew reassignment",
        }),
      });
      // Keep the employee-number display we set optimistically; only the
      // recomputed legality needs reconciling from the response.
      setRows((rs) =>
        rs.map((r) =>
          r.duty_day_key === a.duty_day_key ? { ...r, legality_state: res.legality_state } : r,
        ),
      );
      const bad =
        res.legality_state === "ILLEGAL" || res.legality_state === "REQUIRES_FRMS_DEROGATION";
      toast.show(
        `${role} on ${a.aircraft_reg} → ${newEmpNo} · FTL ${res.legality_state ?? "unknown"}`,
        bad ? "error" : "success",
      );
    } catch (err) {
      setRows(prevRows); // roll back the optimistic move
      toast.show(err instanceof ApiError ? err.message : "Reassignment failed", "error");
    } finally {
      setSavingKey(null);
    }
  }

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const list = await api<Assignment[]>(`/api/v1/roster?date_from=${from}&date_to=${to}`);
        if (!cancelled) setRows(list);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load roster");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [from, to, reloadKey]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api<PublicHoliday[]>(
          `/api/v1/reference/public-holidays?country_code=${holidayCountry}&date_from=${from}&date_to=${to}`,
        );
        if (!cancelled) setHolidays(list);
      } catch {
        if (!cancelled) setHolidays([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [holidayCountry, from, to]);

  const byDate = new Map<string, Assignment[]>();
  for (const r of rows) {
    const list = byDate.get(r.date_local) ?? [];
    list.push(r);
    byDate.set(r.date_local, list);
  }

  const holidayByDate = new Map<string, string>();
  for (const h of holidays) {
    holidayByDate.set(h.date, h.name);
  }

  const days = dateRange(from, to);

  async function autoGenerate() {
    setGenerating(true);
    setDraft(null);
    setDraftMsg(null);
    try {
      const resp = await api<AutoGenerateResponse>("/api/v1/roster/auto-generate", {
        method: "POST",
        body: JSON.stringify({ horizon_from: from, horizon_to: to }),
      });
      setDraft({ result: resp.result, sectors: resp.sectors });
      if (resp.result.assignments.length === 0) {
        const reason =
          (resp.result.diagnostics?.reason as string | undefined) ??
          "No assignments could be made — check crew type ratings and routings.";
        setDraftMsg(reason);
      }
    } catch (err) {
      setDraftMsg(err instanceof ApiError ? err.message : "Auto-generate failed");
    } finally {
      setGenerating(false);
    }
  }

  async function publishDraft() {
    if (!draft || draft.result.assignments.length === 0) return;
    setPublishing(true);
    setDraftMsg(null);
    try {
      await api("/api/v1/roster/publish", {
        method: "POST",
        body: JSON.stringify({
          horizon_from: from,
          horizon_to: to,
          sectors: draft.sectors,
          assignments: draft.result.assignments,
        }),
      });
      setDraft(null);
      setReloadKey((k) => k + 1);
    } catch (err) {
      setDraftMsg(err instanceof ApiError ? err.message : "Publish failed");
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>Roster calendar</CardTitle>
            <div className="flex flex-wrap items-center gap-3 text-sm text-dn-muted">
              {/* Date range */}
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={from}
                  onChange={(e) => setFrom(e.target.value)}
                  className="rounded-md border border-dn-steel-lt px-2 py-1 font-mono"
                  data-testid="roster-date-from"
                />
                <span>→</span>
                <input
                  type="date"
                  value={to}
                  onChange={(e) => setTo(e.target.value)}
                  className="rounded-md border border-dn-steel-lt px-2 py-1 font-mono"
                  data-testid="roster-date-to"
                />
              </div>
              {/* Holiday country picker */}
              <div className="flex items-center gap-1">
                <span className="text-xs text-dn-muted">Holidays:</span>
                <select
                  value={holidayCountry}
                  onChange={(e) => setHolidayCountry(e.target.value)}
                  className="rounded-md border border-dn-steel-lt px-2 py-1 text-xs font-mono"
                  data-testid="holiday-country-select"
                >
                  {COUNTRY_OPTIONS.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
              <Button
                size="sm"
                onClick={autoGenerate}
                disabled={generating}
                data-testid="auto-generate-btn"
              >
                {generating ? "Generating…" : "Auto-generate roster"}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardBody>
          {(draft || draftMsg) && (
            <div
              className="mb-4 rounded-md border border-dn-gold/40 bg-dn-gold/5 p-4"
              data-testid="draft-banner"
            >
              {draft && (
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="text-sm">
                    <span className="font-medium text-dn-dark">
                      Draft roster: {draft.result.status}
                    </span>{" "}
                    <span className="text-dn-muted">
                      · {draft.result.assignments.length} duty days assigned
                      {draft.result.unassigned_duty_days.length > 0 &&
                        ` · ${draft.result.unassigned_duty_days.length} unassigned`}{" "}
                      · solved in {draft.result.elapsed_s.toFixed(1)}s
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setDraft(null);
                        setDraftMsg(null);
                      }}
                    >
                      Discard
                    </Button>
                    <Button
                      size="sm"
                      onClick={publishDraft}
                      disabled={publishing || draft.result.assignments.length === 0}
                      data-testid="publish-draft-btn"
                    >
                      {publishing ? "Publishing…" : "Publish this draft"}
                    </Button>
                  </div>
                </div>
              )}
              {draftMsg && <p className="mt-2 text-sm text-dn-red">{draftMsg}</p>}
            </div>
          )}
          {loading ? (
            <p className="text-sm text-dn-muted">Loading…</p>
          ) : error ? (
            <p className="text-sm text-dn-red">{error}</p>
          ) : (
            <>
              {rows.length > 0 && crew.length > 0 && (
                <div className="mb-3" data-testid="crew-palette">
                  <p className="text-xs text-dn-muted mb-1">
                    Drag a crew member onto a duty&rsquo;s CAPT/FO slot to reassign — the FTL check
                    runs live and the move rolls back if the backend rejects it.
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {crew
                      .filter((c) => c.crew_category === "FLIGHT_DECK" && c.active)
                      .map((c) => (
                        <span
                          key={c.id}
                          draggable
                          onDragStart={(e) => {
                            e.dataTransfer.setData("text/plain", c.employee_no);
                            setDraggingRole(c.role === "CAPT" ? "CAPT" : "FO");
                          }}
                          onDragEnd={() => setDraggingRole(null)}
                          className="cursor-grab rounded-full border border-dn-steel-lt bg-white px-2 py-0.5 text-xs hover:border-dn-gold"
                          data-testid={`crew-chip-${c.employee_no}`}
                          title={`${c.first_name} ${c.last_name} · ${c.role}`}
                        >
                          <span className="font-mono text-dn-steel">{c.employee_no}</span>{" "}
                          {c.first_name} {c.last_name}
                          <span className="ml-1 text-[10px] text-dn-muted">{c.role}</span>
                        </span>
                      ))}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-1 md:grid-cols-7 gap-2" data-testid="roster-calendar">
                {days.map((d) => {
                  const dayAssignments = byDate.get(d) ?? [];
                  const holidayName = holidayByDate.get(d);
                  return (
                    <div
                      key={d}
                      className={[
                        "rounded-md border p-2 min-h-[100px]",
                        holidayName
                          ? "bg-amber-50 border-amber-200"
                          : "bg-dn-fog border-dn-steel-lt",
                      ].join(" ")}
                    >
                      <div className="font-mono text-xs text-dn-steel mb-1">{d}</div>
                      {holidayName && (
                        <div
                          className="text-xs font-medium text-amber-700 mb-1 truncate"
                          title={holidayName}
                        >
                          🏛 {holidayName}
                        </div>
                      )}
                      {dayAssignments.length === 0 ? (
                        <div className="text-xs text-dn-muted">—</div>
                      ) : (
                        <ul className="space-y-1">
                          {dayAssignments.map((a) => (
                            <li
                              key={a.duty_day_key}
                              className="bg-white rounded border border-dn-steel-lt px-2 py-1 text-xs"
                            >
                              <div className="flex items-center justify-between gap-1">
                                <span className="font-mono">{a.aircraft_reg}</span>
                                <Badge tone="steel">{a.aircraft_type}</Badge>
                              </div>
                              <div className="mt-0.5 space-y-0.5">
                                {(["CAPT", "FO"] as const).map((role) => {
                                  const id = role === "CAPT" ? a.captain_id : a.fo_id;
                                  const zoneKey = `${a.duty_day_key}:${role}`;
                                  const isOver = dragOverZone === zoneKey;
                                  const valid =
                                    draggingRole === null || roleFits(draggingRole, role);
                                  const cls =
                                    isOver && valid
                                      ? "bg-dn-gold/30 ring-1 ring-dn-gold"
                                      : draggingRole !== null && valid
                                        ? "ring-1 ring-dn-gold/40"
                                        : draggingRole !== null && !valid
                                          ? "opacity-40"
                                          : "";
                                  return (
                                    <div
                                      key={role}
                                      onDragOver={(e) => {
                                        e.preventDefault();
                                        if (valid) setDragOverZone(zoneKey);
                                      }}
                                      onDragLeave={() =>
                                        setDragOverZone((z) => (z === zoneKey ? null : z))
                                      }
                                      onDrop={(e) => {
                                        e.preventDefault();
                                        setDragOverZone(null);
                                        const emp = e.dataTransfer.getData("text/plain");
                                        if (emp) void reassign(a, role, emp);
                                      }}
                                      className={[
                                        "flex items-center gap-1 rounded px-1 transition-colors",
                                        cls,
                                      ].join(" ")}
                                      data-testid={`slot-${role}-${a.duty_day_key}`}
                                    >
                                      <span className="text-[10px] font-semibold text-dn-steel">
                                        {role}
                                      </span>
                                      <span
                                        draggable
                                        onDragStart={(e) => {
                                          e.dataTransfer.setData("text/plain", id);
                                          const r = crewByEmpNo.get(id)?.role;
                                          setDraggingRole(r === "CAPT" ? "CAPT" : "FO");
                                        }}
                                        onDragEnd={() => setDraggingRole(null)}
                                        className="cursor-grab truncate text-dn-muted"
                                        title="Drag onto another duty to move this crew"
                                      >
                                        {crewLabel(id)}
                                      </span>
                                    </div>
                                  );
                                })}
                              </div>
                              <div className="flex items-center justify-between mt-1">
                                {savingKey === a.duty_day_key ? (
                                  <span className="text-[10px] text-dn-muted">checking FTL…</span>
                                ) : a.legality_state ? (
                                  <Badge tone={legalityTone(a.legality_state)}>
                                    {a.legality_state}
                                  </Badge>
                                ) : (
                                  <span />
                                )}
                                <button
                                  type="button"
                                  onClick={() => setEditing(a)}
                                  className="text-dn-steel underline text-xs"
                                  data-testid={`amend-btn-${a.duty_day_key}`}
                                >
                                  amend
                                </button>
                              </div>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  );
                })}
              </div>
            </>
          )}
          {rows.length === 0 && !loading && !error && (
            <p className="mt-4 text-sm text-dn-muted" data-testid="roster-empty-hint">
              No published assignments in this window. Generate a roster via the optimiser API, then
              publish it to populate this calendar.
            </p>
          )}
        </CardBody>
      </Card>

      <StandbyPanel from={from} to={to} />

      {editing && (
        <AmendModal
          dutyDayKey={editing.duty_day_key}
          initialCaptain={editing.captain_id}
          initialFo={editing.fo_id}
          onClose={() => setEditing(null)}
          onAmended={() => setReloadKey((k) => k + 1)}
        />
      )}
    </div>
  );
}
