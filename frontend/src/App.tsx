import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AuthProvider } from "@/lib/auth";
import { LoginPage } from "@/pages/login";
import { DashboardPage } from "@/pages/dashboard";
import { CrewPage } from "@/pages/crew";
import { CurrencyPage } from "@/pages/currency";
import { LeavePage } from "@/pages/leave";
import { RosterPage } from "@/pages/roster";
import { SettingsPage } from "@/pages/settings";
import { AuditPage } from "@/pages/audit";
import { CrewMePage } from "@/pages/me";

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/crew/me" element={<CrewMePage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="roster" element={<RosterPage />} />
            <Route path="crew" element={<CrewPage />} />
            <Route path="currency" element={<CurrencyPage />} />
            <Route path="leave" element={<LeavePage />} />
            <Route path="audit" element={<AuditPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
