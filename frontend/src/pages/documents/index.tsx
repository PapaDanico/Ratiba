import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { SortableTh } from "@/components/ui/SortableTh";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { useSort } from "@/lib/useSort";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Label } from "@/components/ui/Label";
import { Modal } from "@/components/ui/Modal";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
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
  { value: "MAINTENANCE_AUTH", label: "Maintenance authorisation" },
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

type DocSortKey = "crew" | "type" | "expires" | "state";

export function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [crew, setCrew] = useState<Crew[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const { sort, toggle, sorted } = useSort<DocSortKey>(null);
  const visibleDocs = sorted(docs, {
    crew: (d) => d.crew_name.toLowerCase(),
    type: (d) => d.doc_type,
    // Empty expiry sorts last in asc.
    expires: (d) => d.expiry_date ?? "9999-12-31",
    state: (d) => ({ RED: 0, AMBER: 1, GREEN: 2, NA: 3 })[d.state],
  });

  // Add-form state
  const [crewId, setCrewId] = useState("");
  const [docType, setDocType] = useState<string>(DEFAULT_DOC_TYPE);
  const [docNumber, setDocNumber] = useState("");
  const [authority, setAuthority] = useState("");
  const [issueDate, setIssueDate] = useState("");
  const [expiryDate, setExpiryDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [formErr, setFormErr] = useState<string | null>(null);

  // Delete confirmation state
  const [deleteModal, setDeleteModal] = useState<Doc | null>(null);
  const [deleting, setDeleting] = useState(false);

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

  async function confirmDelete() {
    if (!deleteModal) return;
    setDeleting(true);
    try {
      await api(`/api/v1/documents/${deleteModal.id}`, { method: "DELETE" });
      setReloadKey((k) => k + 1);
      setDeleteModal(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete");
    } finally {
      setDeleting(false);
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
              <Select
                id="doc-crew"
                value={crewId}
                onChange={(e) => setCrewId(e.target.value)}
                required
              >
                {crew.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name} ({c.employee_no})
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="doc-type">Document type</Label>
              <Select
                id="doc-type"
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
                required
              >
                {DOC_TYPES.map((d) => (
                  <option key={d.value} value={d.value}>
                    {d.label}
                  </option>
                ))}
              </Select>
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
          {formErr && <ErrorAlert message={formErr} />}
          <div className="flex justify-end">
            <Button type="submit" disabled={busy || !crewId} data-testid="add-document-submit">
              {busy ? "Adding…" : "Add document"}
            </Button>
          </div>
        </form>

        {loading ? (
          <TableSkeleton rows={6} cols={8} />
        ) : error ? (
          <ErrorAlert message={error} />
        ) : docs.length === 0 ? (
          <EmptyState
            icon="📄"
            title="No documents recorded yet"
            hint="Record licences, medicals and certificates with the form above to track their expiry here."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="rtable min-w-full text-sm" data-testid="documents-table">
              <thead className="sticky-head text-left text-dn-muted border-b border-dn-steel-lt">
                <tr>
                  <th className="py-3 pr-4 font-medium">
                    <SortableTh label="Crew" col="crew" sort={sort} onSort={toggle} />
                  </th>
                  <th className="py-3 pr-4 font-medium">
                    <SortableTh label="Type" col="type" sort={sort} onSort={toggle} />
                  </th>
                  <th className="py-3 pr-4 font-medium">Number</th>
                  <th className="py-3 pr-4 font-medium">Authority</th>
                  <th className="py-3 pr-4 font-medium">
                    <SortableTh label="Expires" col="expires" sort={sort} onSort={toggle} />
                  </th>
                  <th className="py-3 pr-4 font-medium">Days left</th>
                  <th className="py-3 pr-4 font-medium">
                    <SortableTh label="State" col="state" sort={sort} onSort={toggle} />
                  </th>
                  <th className="py-3 pr-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dn-steel-lt">
                {visibleDocs.map((d) => (
                  <tr key={d.id}>
                    <td data-label="Crew" className="py-3 pr-4">
                      <span className="text-dn-dark">{d.crew_name}</span>{" "}
                      <span className="font-mono text-xs text-dn-muted">({d.employee_no})</span>
                    </td>
                    <td data-label="Type" className="py-3 pr-4">
                      {label(d.doc_type)}
                    </td>
                    <td data-label="Number" className="py-3 pr-4 font-mono text-xs">
                      {d.document_number ?? "—"}
                    </td>
                    <td data-label="Authority" className="py-3 pr-4 text-xs">
                      {d.issuing_authority ?? "—"}
                    </td>
                    <td data-label="Expires" className="py-3 pr-4 font-mono">
                      {d.expiry_date ?? "—"}
                    </td>
                    <td data-label="Days left" className="py-3 pr-4 font-mono">
                      {d.days_remaining === null ? "—" : d.days_remaining}
                    </td>
                    <td data-label="State" className="py-3 pr-4">
                      {d.state === "NA" ? (
                        <span className="text-xs text-dn-muted">no expiry</span>
                      ) : (
                        <Badge tone={tone(d.state)}>{d.state}</Badge>
                      )}
                    </td>
                    <td data-label="" className="py-2 pr-4">
                      <button
                        type="button"
                        onClick={() => setDeleteModal(d)}
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

        {deleteModal && (
          <Modal
            title="Remove document"
            onClose={() => setDeleteModal(null)}
            disableEscape={deleting}
          >
            <div className="space-y-4">
              <p className="text-sm text-dn-dark">
                Remove {deleteModal.doc_type} document for {deleteModal.crew_name}? This action
                cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <Button
                  variant="secondary"
                  onClick={() => setDeleteModal(null)}
                  disabled={deleting}
                >
                  Cancel
                </Button>
                <Button variant="danger" onClick={confirmDelete} disabled={deleting}>
                  {deleting ? "Removing…" : "Remove"}
                </Button>
              </div>
            </div>
          </Modal>
        )}
      </CardBody>
    </Card>
  );
}
