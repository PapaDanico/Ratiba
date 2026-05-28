import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

type CurrencyStatus = {
  crew_id: string;
  currency_type: string;
  expires_date: string;
  days_remaining: number;
  state: "GREEN" | "AMBER" | "RED";
};

type LeaveRequest = {
  id: string;
  status: string;
};

export function DashboardPage() {
  const { user } = useAuth();
  const [pendingLeave, setPendingLeave] = useState<number>(0);
  const [currencyCounts, setCurrencyCounts] = useState({
    green: 0,
    amber: 0,
    red: 0,
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [pending, currencies] = await Promise.all([
          api<LeaveRequest[]>("/api/v1/leave?status=PENDING"),
          api<CurrencyStatus[]>("/api/v1/crew/currency/dashboard"),
        ]);
        if (cancelled) return;
        setPendingLeave(pending.length);
        const counts = { green: 0, amber: 0, red: 0 };
        for (const c of currencies) {
          if (c.state === "GREEN") counts.green++;
          else if (c.state === "AMBER") counts.amber++;
          else counts.red++;
        }
        setCurrencyCounts(counts);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-dn-dark">
          Welcome back, {user?.full_name.split(" ")[0]}
        </h1>
        <p className="mt-1 text-dn-muted text-sm">
          Operations overview — KCARs 2025 Part 8 baseline.
        </p>
      </div>
      {error && (
        <Card>
          <CardBody className="text-sm text-dn-red">{error}</CardBody>
        </Card>
      )}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Pending leave</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="font-display text-5xl text-dn-dark" data-testid="pending-leave-count">
              {pendingLeave}
            </div>
            <p className="mt-2 text-sm text-dn-muted">Requests awaiting your decision.</p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Currency status</CardTitle>
          </CardHeader>
          <CardBody className="space-y-2">
            <div className="flex items-center justify-between">
              <Badge tone="green">Current</Badge>
              <span className="font-mono text-dn-dark">{currencyCounts.green}</span>
            </div>
            <div className="flex items-center justify-between">
              <Badge tone="amber">Expiring ≤ 30 d</Badge>
              <span className="font-mono text-dn-dark">{currencyCounts.amber}</span>
            </div>
            <div className="flex items-center justify-between">
              <Badge tone="red">Expired</Badge>
              <span className="font-mono text-dn-dark">{currencyCounts.red}</span>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>This week</CardTitle>
          </CardHeader>
          <CardBody>
            <p className="text-sm text-dn-muted">
              Roster calendar lives under{" "}
              <a href="/roster" className="text-dn-steel underline">
                Roster
              </a>
              . FTL violations show inline before publication.
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
