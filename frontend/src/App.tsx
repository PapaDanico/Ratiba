import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AuthProvider } from "@/lib/auth";
import { ToastProvider } from "@/lib/toast";
import { HomePage } from "@/pages/home";
import { LoginPage } from "@/pages/login";
import { DashboardPage } from "@/pages/dashboard";
import { CrewPage } from "@/pages/crew";
import { CurrencyPage } from "@/pages/currency";
import { TrainingPage } from "@/pages/training";
import { DocumentsPage } from "@/pages/documents";
import { LeavePage } from "@/pages/leave";
import { RosterPage } from "@/pages/roster";
import { RoutingsPage } from "@/pages/routings";
import { SettingsPage } from "@/pages/settings";
import { AuditPage } from "@/pages/audit";
import { CrewMePage } from "@/pages/me";
import { SwapsPage } from "@/pages/swaps";
import { NoticesPage } from "@/pages/notices";
import { PostingsPage } from "@/pages/postings";
import { FatiguePage } from "@/pages/fatigue";
import { IropPage } from "@/pages/irop";
import { FleetPage } from "@/pages/fleet";
import { ConstraintsPage } from "@/pages/constraints";
import { PrivacyPage } from "@/pages/legal/privacy";
import { TermsPage } from "@/pages/legal/terms";
import { ImportPage } from "@/pages/import";
import { ErrorPage } from "@/pages/error";

export function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/privacy" element={<PrivacyPage />} />
              <Route path="/terms" element={<TermsPage />} />
              <Route path="/crew/me" element={<CrewMePage />} />
              <Route
                path="/app"
                element={
                  <ProtectedRoute>
                    <AppShell />
                  </ProtectedRoute>
                }
              >
                <Route index element={<DashboardPage />} />
                <Route path="routings" element={<RoutingsPage />} />
                <Route path="roster" element={<RosterPage />} />
                <Route path="crew" element={<CrewPage />} />
                <Route path="postings" element={<PostingsPage />} />
                <Route path="import" element={<ImportPage />} />
                <Route path="training" element={<TrainingPage />} />
                <Route path="documents" element={<DocumentsPage />} />
                <Route path="currency" element={<CurrencyPage />} />
                <Route path="leave" element={<LeavePage />} />
                <Route path="swaps" element={<SwapsPage />} />
                <Route path="notices" element={<NoticesPage />} />
                <Route path="fleet" element={<FleetPage />} />
                <Route path="constraints" element={<ConstraintsPage />} />
                <Route path="fatigue" element={<FatiguePage />} />
                <Route path="irop" element={<IropPage />} />
                <Route path="audit" element={<AuditPage />} />
                <Route path="settings" element={<SettingsPage />} />
              </Route>
              <Route path="*" element={<ErrorPage />} />
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}
