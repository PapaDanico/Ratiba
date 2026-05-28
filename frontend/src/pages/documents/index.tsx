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

type Doc = {
  id: string;
  crew_id: string;
  employee_no: string;
  crew_name: string;
  doc_type: string;
  document_number: string | null;
  issuing_authority: string | null;
  issue_date: string | null;
  expiry_date: string | null;
  file_ref: string | null;
  notes: string | null;
  days_remaining: number | null;
  state: "GREEN" | "AMBER" | "RED" | "NA";
};

const DOC_TYPES = [
  { value: "LICENCE", label: "Licence (CPL/ATPL)" },
  { value: "MEDICAL", label: "Medical certificate" },
  { value: "TYPE_RATING_CERT", label: "Type rating certificate" },
  { value: "PASSPORT", label: "Passport" },
  { value: "VISA", label: "Visa" },
  { value: "WORK_PERMIT", label: "Work permit" },
  { value: "OTHER", label: "Other" },
] as const;

const DEFAULT_DOC_TYPE = "LICENCE";

function tone(state: Doc["state"]): "green" | "amber" | "red" | "neutral" {
  if (state === "GREEN") return "green";
  if (state === "AMBER") return "amber";
  if (state === "RED") return "red";
  return "neutral";
}

function label(value: string): string {
  return DOC_TYPES.find((d) => d.value === value)?.label ?? value;
}

export function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [crew, setCrew] = useState<Crew[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // Add-form state
  const [crewId, setCrewId] = useState("");
  const [docType, setDocType] = useState<string>(DEFAULT_DOC_TYPE);
  const [docNumber, setDocNumber] = useState("");
  const [authority, setAuthority] = useState("");
  const [issueDate, setIssueDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [formErr, setFormErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const c = await api<Crew[]>("/api/v1/crew");
        if (!cancelled) {
          setCrew(c);
          if (c[0]) setCrewId(c[0].id);
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
    setLoading(true);
    (async () => {
      try {
        const list = await api<Doc[]>("/api/v1/documents");
        if (!cancelled) setDocs(list);
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
      await api(`/api/v1/documents/crew/${crewId}`, {
        method: "POST",
        body: JSON.stringify({
          doc_type: docType,
          document_number: docNumber.trim() || null,
          issuing_authority: authority.trim() || null,
          issue_date: issueDate || null,
          expiry_date: expiryDate || null,
        }),
      });
      setDocNumber("");
      setAuthority("");
      setIssueDate("");
      setExpiryDate("");
      setReloadKey((k) => k + 1);
    } catch (err) {
      setFormErr(err instanceof ApiError ? err.message : "Failed to add document");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    try {
      await api(`/api/v1/documents/${id}`, { method: "DELETE" });
      setReloadKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Crew documents</CardTitle>
      </CardHeader>
      <CardBody>
        <p className="text-sm text-dn-muted mb-4">
          Track licences, medicals, passports, visas and work permits. Documents with an expiry date
          feed the Training → Recurrency dashboard so nothing lapses unnoticed.
        </p>

        <form onSubmit={add} className="mb-6 space-y-3" data-testid="add-document-form">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div>
              <Label htmlFor="doc-crew">Crew</Label>
              <select
                id="doc-crew"
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
              <Label htmlFor="doc-type">Document type</Label>
              <select
                id="doc-type"
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                className="w-full rounded-md border border-dn-steel-lt px-2 py-2 text-sm"
                required
              >
                {DOC_TYPES.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <Label htmlFor="doc-number">Document no.</Label>
              <Input
                id="doc-number"
                value={docNumber}
                onChange={(e) => setDocNumber(e.target.value)}
                placeholder="optional"
              />
            </div>
            <div>
              <Label htmlFor="doc-authority">Issuing authority</Label>
              <Input
                id="doc-authority"
                value={authority}
                onChange={(e) => setAuthority(e.target.value)}
                placeholder="e.g. KCAA"
              />
            </div>
            <div>
              <Label htmlFor="doc-issue">Issue date</Label>
              <Input
                id="doc-issue"
                type="date"
                value={issueDate}
                onChange={(e) => setIssueDate(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="doc-expiry">Expiry date</Label>
              <Input
                id="doc-expiry"
                type="date"
                value={expiryDate}
                onChange={(e) => setExpiryDate(e.target.value)}
              />
            </div>
          </div>
          {formErr && <p className="text-sm text-dn-red">{formErr}</p>}
          <div className="flex justify-end">
            <Button type="submit" disabled={busy || !crewId} data-testid="add-document-submit">
              {busy ? "Adding…" : "Add document"}
            </Button>
          </div>
        </form>

        {loading ? (
          <p className="text-sm text-dn-muted">Loading…</p>
        ) : error ? (
          <p className="text-sm text-dn-red">{error}</p>
        ) : docs.length === 0 ? (
          <p className="text-sm text-dn-muted" data-testid="documents-empty">
            No documents recorded yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm" data-testid="documents-table">
              <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                <tr>
                  <th className="py-2 pr-4 font-medium">Crew</th>
                  <th className="py-2 pr-4 font-medium">Type</th>
                  <th className="py-2 pr-4 font-medium">Number</th>
                  <th className="py-2 pr-4 font-medium">Authority</th>
                  <th className="py-2 pr-4 font-medium">Expires</th>
                  <th className="py-2 pr-4 font-medium">Days left</th>
                  <th className="py-2 pr-4 font-medium">State</th>
                  <th className="py-2 pr-4 font-medium" />
                </tr>
              </thead>
              <tbody className="divide-y divide-dn-steel-lt">
                {docs.map((d) => (
                  <tr key={d.id} className="hover:bg-dn-fog">
                    <td className="py-2 pr-4">
                      <span className="text-dn-dark">{d.crew_name}</span>{" "}
                      <span className="font-mono text-xs text-dn-muted">({d.employee_no})</span>
                    </td>
                    <td className="py-2 pr-4">{label(d.doc_type)}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{d.document_number ?? "—"}</td>
                    <td className="py-2 pr-4 text-xs">{d.issuing_authority ?? "—"}</td>
                    <td className="py-2 pr-4 font-mono">{d.expiry_date ?? "—"}</td>
                    <td className="py-2 pr-4 font-mono">
                      {d.days_remaining === null ? "—" : d.days_remaining}
                    </td>
                    <td className="py-2 pr-4">
                      {d.state === "NA" ? (
                        <span className="text-xs text-dn-muted">no expiry</span>
                      ) : (
                        <Badge tone={tone(d.state)}>{d.state}</Badge>
                      )}
                    </td>
                    <td className="py-2 pr-4">
                      <button
                        type="button"
                        onClick={() => remove(d.id)}
                        className="text-dn-red underline text-xs"
                        data-testid={`delete-document-${d.id}`}
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
