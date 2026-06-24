import { useQuery } from "@tanstack/react-query";
import { Navigate, Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { api } from "../api/client";
import type { User, AdminReportResponse } from "../api/types";

interface AdminDashboardPageProps {
  user: User;
}

function StatCard({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-gray-100">
        {value}
      </p>
    </div>
  );
}

function BreakdownCard({
  title,
  data,
}: {
  title: string;
  data: Record<string, number>;
}) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((sum, [, v]) => sum + v, 0);

  return (
    <Card title={title}>
      {entries.length === 0 ? (
        <p className="text-sm text-gray-500">No data.</p>
      ) : (
        <ul className="space-y-2">
          {entries.map(([key, count]) => {
            const pct = total > 0 ? Math.round((count / total) * 100) : 0;
            return (
              <li key={key}>
                <div className="flex items-center justify-between text-sm">
                  <span className="capitalize text-gray-700 dark:text-gray-300">
                    {key.replace(/_/g, " ")}
                  </span>
                  <span className="font-medium text-gray-900 dark:text-gray-100">
                    {count}
                  </span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
                  <div
                    className="h-full rounded-full bg-blue-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

export function AdminDashboardPage({ user }: AdminDashboardPageProps) {
  const reportQuery = useQuery<AdminReportResponse>({
    queryKey: ["admin-reports"],
    queryFn: () => api.get<AdminReportResponse>("/admin/reports"),
    enabled: user.is_admin,
  });

  async function handleLogout() {
    try {
      await api.post("/logout");
    } catch {
      /* fall through */
    }
    window.location.href = "/login";
  }

  if (!user.is_admin) {
    return <Navigate to="/" replace />;
  }

  const byStatus = reportQuery.data?.by_status ?? {};
  const byPriority = reportQuery.data?.by_priority ?? {};
  const byAgent = reportQuery.data?.by_agent ?? {};
  const total = Object.values(byStatus).reduce((s, v) => s + v, 0);

  return (
    <AppShell user={user} onLogout={handleLogout}>
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Admin Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Support ticket analytics and reports.
          </p>
        </div>

        {reportQuery.isLoading ? (
          <div className="py-12 text-center text-sm text-gray-500">
            Loading reports…
          </div>
        ) : reportQuery.isError ? (
          <Card>
            <p className="text-center text-sm text-red-600">
              Failed to load reports.
            </p>
          </Card>
        ) : (
          <>
            <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard label="Total Tickets" value={total} />
              <StatCard
                label="Open"
                value={byStatus["open"] ?? 0}
              />
              <StatCard
                label="In Progress"
                value={byStatus["in_progress"] ?? 0}
              />
              <StatCard
                label="Resolved"
                value={(byStatus["resolved"] ?? 0) + (byStatus["closed"] ?? 0)}
              />
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <BreakdownCard title="By Status" data={byStatus} />
              <BreakdownCard title="By Priority" data={byPriority} />
              <BreakdownCard title="By Agent" data={byAgent} />
            </div>
          </>
        )}

        <div className="mt-6">
          <Link to="/">
            <Button variant="secondary">View All Tickets</Button>
          </Link>
        </div>
      </div>
    </AppShell>
  );
}
