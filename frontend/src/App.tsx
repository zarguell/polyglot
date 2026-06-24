import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LoginPage } from "./auth/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { AuthGuard } from "./auth/AuthGuard";
import { TicketListPage } from "./pages/TicketListPage";
import { TicketFormPage } from "./pages/TicketFormPage";
import { TicketDetailPage } from "./pages/TicketDetailPage";
import { AgentQueuePage } from "./pages/AgentQueuePage";
import { AdminDashboardPage } from "./pages/AdminDashboardPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={
              <AuthGuard>{(user) => <TicketListPage user={user} />}</AuthGuard>
            }
          />
          <Route path="/tickets/new" element={<TicketFormPage />} />
          <Route
            path="/tickets/:id"
            element={
              <AuthGuard>
                {(user) => <TicketDetailPage user={user} />}
              </AuthGuard>
            }
          />
          <Route
            path="/queue"
            element={
              <AuthGuard>
                {(user) => <AgentQueuePage user={user} />}
              </AuthGuard>
            }
          />
          <Route
            path="/admin"
            element={
              <AuthGuard>
                {(user) => <AdminDashboardPage user={user} />}
              </AuthGuard>
            }
          />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/dashboard"
            element={
              <AuthGuard>
                {(user) => <DashboardPage user={user} />}
              </AuthGuard>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
