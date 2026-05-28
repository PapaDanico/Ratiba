import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api, ApiError } from "@/lib/api";

type Crew = {
  id: string;
  employee_no: string;
  first_name: string;
  last_name: string;
  role: "CAPT" | "FO" | "SO";
  base_station: string;
  contract_type: string;
  active: boolean;
};

export function CrewPage() {
  const [rows, setRows] = useState<Crew[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api<Crew[]>("/api/v1/crew");
        if (!cancelled) setRows(list);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load crew");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Crew roster</CardTitle>
      </CardHeader>
      <CardBody>
        {loading ? (
          <p className="text-sm text-dn-muted">Loading…</p>
        ) : error ? (
          <p className="text-sm text-dn-red">{error}</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-dn-muted">
            No crew yet. Create one via the API or wait for the import flow in Phase 6.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm" data-testid="crew-table">
              <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                <tr>
                  <th className="py-2 pr-4 font-medium">Employee #</th>
                  <th className="py-2 pr-4 font-medium">Name</th>
                  <th className="py-2 pr-4 font-medium">Role</th>
                  <th className="py-2 pr-4 font-medium">Base</th>
                  <th className="py-2 pr-4 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dn-steel-lt">
                {rows.map((c) => (
                  <tr key={c.id} className="hover:bg-dn-fog">
                    <td className="py-2 pr-4 font-mono text-dn-steel">{c.employee_no}</td>
                    <td className="py-2 pr-4 text-dn-dark">
                      {c.first_name} {c.last_name}
                    </td>
                    <td className="py-2 pr-4">
                      <Badge tone="steel">{c.role}</Badge>
                    </td>
                    <td className="py-2 pr-4 font-mono">{c.base_station}</td>
                    <td className="py-2 pr-4">
                      {c.active ? (
                        <Badge tone="green">Active</Badge>
                      ) : (
                        <Badge tone="neutral">Inactive</Badge>
                      )}
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
