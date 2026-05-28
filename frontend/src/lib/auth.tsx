/** Auth context — current user + login state. */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, login as apiLogin, logout as apiLogout, tokenStore } from "./api";

export type CurrentUser = {
  id: string;
  email: string;
  full_name: string;
  role: "CREWING_OFFICER" | "CHIEF_PILOT" | "ADMIN" | "PILOT";
  operator_id: string;
  is_active: boolean;
};

type AuthContextValue = {
  user: CurrentUser | null;
  status: "unknown" | "authenticated" | "anonymous" | "loading";
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [status, setStatus] = useState<AuthContextValue["status"]>("unknown");

  const refreshMe = useCallback(async () => {
    if (!tokenStore.getAccess()) {
      setStatus("anonymous");
      setUser(null);
      return;
    }
    try {
      const me = await api<CurrentUser>("/api/v1/auth/me");
      setUser(me);
      setStatus("authenticated");
    } catch {
      tokenStore.clear();
      setUser(null);
      setStatus("anonymous");
    }
  }, []);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      setStatus("loading");
      try {
        await apiLogin(email, password);
        await refreshMe();
      } catch (err) {
        setStatus("anonymous");
        throw err;
      }
    },
    [refreshMe],
  );

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
    setStatus("anonymous");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, status, login, logout }),
    [user, status, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
