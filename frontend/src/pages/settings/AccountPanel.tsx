import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api, ApiError } from "@/lib/api";

type Account = {
  id: string;
  email: string;
  full_name: string;
  role: "CREWING_OFFICER" | "CHIEF_PILOT" | "ADMIN" | "PILOT";
};

const ROLE_LABEL: Record<Account["role"], string> = {
  CREWING_OFFICER: "Crewing officer",
  CHIEF_PILOT: "Chief pilot",
  ADMIN: "Administrator",
  PILOT: "Pilot",
};

export function AccountPanel() {
  const [account, setAccount] = useState<Account | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);

  // Profile (display name)
  const [fullName, setFullName] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [nameErr, setNameErr] = useState<string | null>(null);
  const [nameOk, setNameOk] = useState(false);

  // Password
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [savingPw, setSavingPw] = useState(false);
  const [pwErr, setPwErr] = useState<string | null>(null);
  const [pwOk, setPwOk] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await api<Account>("/api/v1/settings/account");
        if (!cancelled) {
          setAccount(me);
          setFullName(me.full_name);
        }
      } catch (err) {
        if (!cancelled) setLoadErr(err instanceof ApiError ? err.message : "Failed to load");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function saveName(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSavingName(true);
    setNameErr(null);
    setNameOk(false);
    try {
      const updated = await api<Account>("/api/v1/settings/account", {
        method: "PATCH",
        body: JSON.stringify({ full_name: fullName }),
      });
      setAccount(updated);
      setNameOk(true);
    } catch (err) {
      setNameErr(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSavingName(false);
    }
  }

  async function savePassword(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPwErr(null);
    setPwOk(false);
    if (next !== confirm) {
      setPwErr("New password and confirmation do not match.");
      return;
    }
    setSavingPw(true);
    try {
      await api("/api/v1/settings/account/password", {
        method: "POST",
        body: JSON.stringify({ current_password: current, new_password: next }),
      });
      setPwOk(true);
      setCurrent("");
      setNext("");
      setConfirm("");
    } catch (err) {
      setPwErr(err instanceof ApiError ? err.message : "Could not change password");
    } finally {
      setSavingPw(false);
    }
  }

  if (loadErr) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-dn-red">{loadErr}</p>
        </CardBody>
      </Card>
    );
  }
  if (!account) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-dn-muted">Loading…</p>
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>My profile</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={saveName} className="space-y-4 max-w-xl">
            <div>
              <Label>Email</Label>
              <Input value={account.email} disabled />
              <p className="mt-1 text-xs text-dn-muted">
                Signed in as {ROLE_LABEL[account.role]}. Contact an administrator to change your
                email or role.
              </p>
            </div>
            <div>
              <Label htmlFor="acct-name">Display name</Label>
              <Input
                id="acct-name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                data-testid="account-name"
              />
            </div>
            {nameErr && <p className="text-sm text-dn-red">{nameErr}</p>}
            {nameOk && <p className="text-sm text-dn-green">Saved.</p>}
            <Button type="submit" disabled={savingName} data-testid="account-name-save">
              {savingName ? "Saving…" : "Save profile"}
            </Button>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Change password</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={savePassword} className="space-y-4 max-w-xl">
            <div>
              <Label htmlFor="pw-current">Current password</Label>
              <Input
                id="pw-current"
                type="password"
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                required
                data-testid="pw-current"
              />
            </div>
            <div>
              <Label htmlFor="pw-new">New password</Label>
              <Input
                id="pw-new"
                type="password"
                autoComplete="new-password"
                value={next}
                onChange={(e) => setNext(e.target.value)}
                required
                minLength={8}
                data-testid="pw-new"
              />
              <p className="mt-1 text-xs text-dn-muted">At least 8 characters.</p>
            </div>
            <div>
              <Label htmlFor="pw-confirm">Confirm new password</Label>
              <Input
                id="pw-confirm"
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                minLength={8}
                data-testid="pw-confirm"
              />
            </div>
            {pwErr && <p className="text-sm text-dn-red">{pwErr}</p>}
            {pwOk && <p className="text-sm text-dn-green">Password changed.</p>}
            <Button type="submit" disabled={savingPw} data-testid="pw-save">
              {savingPw ? "Changing…" : "Change password"}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
