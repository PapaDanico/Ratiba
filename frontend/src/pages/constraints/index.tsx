import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api, ApiError } from "@/lib/api";

type SetStatus = "UNDER_REVIEW" | "ACCEPTED" | "REJECTED";
type ReviewStatus = "PROPOSED" | "ACCEPTED" | "EDITED" | "REJECTED";

type Rule = {
  id: string;
  rule_key: string;
  proposed_value: number | null;
  baseline_value: number | null;
  final_value: number | null;
  review_status: ReviewStatus;
  regulation_ref: string | null;
  source_excerpt: string | null;
  confidence: number | null;
  differs_from_baseline: boolean;
};

type SetSummary = {
  id: string;
  om_a_revision: string;
  source_filename: string | null;
  status: SetStatus;
  model: string | null;
  coverage_pct: number | null;
  rule_count: number;
  accepted_at: string | null;
  created_at: string;
};

type SetDetail = SetSummary & { rules: Rule[] };

function statusTone(s: ReviewStatus): "green" | "amber" | "red" | "steel" {
  if (s === "ACCEPTED") return "green";
  if (s === "EDITED") return "amber";
  if (s === "REJECTED") return "red";
  return "steel";
}

export function ConstraintsPage() {
  const [sets, setSets] = useState<SetSummary[]>([]);
  const [active, setActive] = useState<SetDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [revision, setRevision] = useState("");
  const [filename, setFilename] = useState("");
  const [text, setText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [onlyChanges, setOnlyChanges] = useState(true);

  async function reloadSets() {
    try {
      setSets(await api<SetSummary[]>("/api/v1/constraints"));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load constraint sets");
    }
  }

  useEffect(() => {
    void reloadSets();
  }, []);

  async function openSet(id: string) {
    try {
      setActive(await api<SetDetail>(`/api/v1/constraints/${id}`));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load set");
    }
  }

  async function parse(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setParsing(true);
    setError(null);
    try {
      const detail = await api<SetDetail>("/api/v1/constraints/parse", {
        method: "POST",
        body: JSON.stringify({
          om_a_revision: revision.trim(),
          om_a_text: text,
          source_filename: filename.trim() || null,
        }),
      });
      setRevision("");
      setFilename("");
      setText("");
      setActive(detail);
      await reloadSets();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Parse failed");
    } finally {
      setParsing(false);
    }
  }

  async function review(rule: Rule, status: ReviewStatus) {
    if (!active) return;
    let finalValue: number | null = null;
    if (status === "EDITED") {
      const raw = window.prompt(
        `New value for ${rule.rule_key}`,
        String(rule.proposed_value ?? ""),
      );
      if (raw === null) return;
      finalValue = Number(raw);
      if (Number.isNaN(finalValue)) {
        setError("Edited value must be a number");
        return;
      }
    }
    try {
      await api(`/api/v1/constraints/${active.id}/rules/${rule.id}`, {
        method: "PATCH",
        body: JSON.stringify({ review_status: status, final_value: finalValue }),
      });
      await openSet(active.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Review failed");
    }
  }

  async function acceptSet() {
    if (!active) return;
    try {
      const detail = await api<SetDetail>(`/api/v1/constraints/${active.id}/accept`, {
        method: "POST",
      });
      setActive(detail);
      await reloadSets();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Acceptance failed");
    }
  }

  const proposals = active?.rules.filter((r) => r.proposed_value !== null) ?? [];
  const pending = proposals.filter((r) => r.review_status === "PROPOSED").length;
  const visibleRules = (active?.rules ?? []).filter(
    (r) => !onlyChanges || r.differs_from_baseline || r.review_status !== "PROPOSED",
  );

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Parse an OM-A FTL chapter</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={parse} className="space-y-4" data-testid="parse-form">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="rev">OM-A revision</Label>
                <Input
                  id="rev"
                  value={revision}
                  onChange={(e) => setRevision(e.target.value)}
                  placeholder="e.g. Rev 7 (2026-03)"
                  required
                  data-testid="parse-revision"
                />
              </div>
              <div>
                <Label htmlFor="fn">Source filename (optional)</Label>
                <Input
                  id="fn"
                  value={filename}
                  onChange={(e) => setFilename(e.target.value)}
                  placeholder="om-a-ch7-ftl.pdf"
                  data-testid="parse-filename"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="omtext">FTL chapter text</Label>
              <textarea
                id="omtext"
                value={text}
                onChange={(e) => setText(e.target.value)}
                required
                rows={8}
                className="block w-full rounded-md border border-dn-steel-lt bg-white px-3 py-2 text-sm font-mono"
                placeholder="Paste the operator's flight-time-limitation chapter here…"
                data-testid="parse-text"
              />
            </div>
            {error && <p className="text-sm text-dn-red">{error}</p>}
            <Button type="submit" disabled={parsing} data-testid="parse-submit">
              {parsing ? "Parsing with Claude…" : "Parse + review"}
            </Button>
            <p className="text-xs text-dn-muted">
              Claude extracts the operator&apos;s numeric limits and diffs them against the KCARs
              2025 baseline. You review every proposed change before it&apos;s accepted.
            </p>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Constraint sets</CardTitle>
        </CardHeader>
        <CardBody>
          {sets.length === 0 ? (
            <p className="text-sm text-dn-muted">No constraint sets yet.</p>
          ) : (
            <ul className="divide-y divide-dn-steel-lt">
              {sets.map((s) => (
                <li key={s.id} className="flex items-center justify-between py-2">
                  <div>
                    <span className="font-medium">{s.om_a_revision}</span>{" "}
                    <span className="text-xs text-dn-muted">
                      {s.coverage_pct ?? 0}% coverage · {s.rule_count} rules · {s.model ?? "—"}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge tone={s.status === "ACCEPTED" ? "green" : "steel"}>{s.status}</Badge>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => void openSet(s.id)}
                      data-testid={`open-set-${s.id}`}
                    >
                      Review
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      {active && (
        <Card>
          <CardHeader>
            <CardTitle>
              {active.om_a_revision} — {proposals.length} proposed change(s)
            </CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={onlyChanges}
                  onChange={(e) => setOnlyChanges(e.target.checked)}
                  data-testid="only-changes"
                />
                Show changes &amp; reviewed only
              </label>
              {active.status === "UNDER_REVIEW" && (
                <Button
                  onClick={() => void acceptSet()}
                  disabled={pending > 0}
                  data-testid="accept-set"
                >
                  {pending > 0 ? `${pending} proposal(s) to review` : "Accept constraint set"}
                </Button>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-dn-muted">
                  <tr className="border-b border-dn-steel-lt">
                    <th className="py-2 pr-3">Rule</th>
                    <th className="py-2 pr-3">Baseline</th>
                    <th className="py-2 pr-3">Proposed</th>
                    <th className="py-2 pr-3">Final</th>
                    <th className="py-2 pr-3">Conf.</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2">Review</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRules.map((r) => (
                    <tr key={r.id} className="border-b border-dn-fog align-top">
                      <td className="py-2 pr-3 font-mono text-xs">
                        {r.rule_key}
                        {r.source_excerpt && (
                          <div className="mt-1 max-w-xs text-dn-muted italic">
                            “{r.source_excerpt}”
                          </div>
                        )}
                      </td>
                      <td className="py-2 pr-3">{r.baseline_value ?? "—"}</td>
                      <td className="py-2 pr-3">
                        {r.proposed_value === null ? (
                          <span className="text-dn-muted">—</span>
                        ) : (
                          <span
                            className={r.differs_from_baseline ? "font-semibold text-dn-gold" : ""}
                          >
                            {r.proposed_value}
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-3">{r.final_value ?? "—"}</td>
                      <td className="py-2 pr-3">
                        {r.confidence === null ? "—" : `${Math.round(r.confidence * 100)}%`}
                      </td>
                      <td className="py-2 pr-3">
                        <Badge tone={statusTone(r.review_status)}>{r.review_status}</Badge>
                      </td>
                      <td className="py-2">
                        {active.status === "UNDER_REVIEW" && r.proposed_value !== null && (
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={() => void review(r, "ACCEPTED")}
                            >
                              Accept
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => void review(r, "EDITED")}
                            >
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => void review(r, "REJECTED")}
                            >
                              Reject
                            </Button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
