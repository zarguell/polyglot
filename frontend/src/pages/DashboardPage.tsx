import { useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { api } from "../api/client";
import type { User, InstalledComponent, Role } from "../api/types";
import { ApiClientError } from "../api/client";

interface DashboardShellProps {
  user: User;
}

export function DashboardPage({ user }: DashboardShellProps) {
  const [components, setComponents] = useState<InstalledComponent[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [permCount, setPermCount] = useState(0);

  useEffect(() => {
    // Fetch component and role data
    api
      .get<InstalledComponent[]>("/system/components")
      .then(setComponents)
      .catch(() => {});
    api
      .get<{ roles: Role[]; permission_count: number }>("/me/roles")
      .then((data) => {
        setRoles(data.roles);
        setPermCount(data.permission_count);
      })
      .catch(() => {});
  }, []);

  async function handleLogout() {
    try {
      await api.post("/logout");
    } catch (e) {
      // If CSRF fails, use full-page navigation to backend logout
      if (e instanceof ApiClientError && e.status === 403) {
        // redirect via navigation to backend
      }
    }
    // Force full page reload to clear state
    window.location.href = "/";
  }

  return (
    <AppShell user={user} onLogout={handleLogout}>
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Application shell is healthy. Ready for business modules.
          </p>
        </div>

        {/* User info */}
        <Card title="Signed In" className="mb-6">
          <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Name</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">
                {user.display_name}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Email</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">
                {user.email}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Provider</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">
                {user.auth_provider}
              </dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Role</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">
                {user.is_admin ? "Admin" : "User"}
              </dd>
            </div>
            {roles.length > 0 && (
              <>
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">
                    RBAC Roles
                  </dt>
                  <dd className="font-medium text-gray-900 dark:text-gray-100">
                    {roles.map((r) => r.name).join(", ") || "None"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">
                    Permissions
                  </dt>
                  <dd className="font-medium text-gray-900 dark:text-gray-100">
                    {permCount} granted
                  </dd>
                </div>
              </>
            )}
          </dl>
        </Card>

        {/* Component status */}
        <Card title="Installed Components" className="mb-6">
          {components.length > 0 ? (
            <ul className="divide-y divide-gray-100 dark:divide-gray-800">
              {components.map((c) => (
                <li
                  key={c.id}
                  className="flex items-center justify-between py-3"
                >
                  <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                    {c.name}
                  </span>
                  <span className="text-xs text-gray-400">v{c.version}</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No Business Modules Installed"
              description="Drop a PRD into docs/ and an AI agent will build your app inside this scaffold."
            />
          )}
        </Card>

        {/* App Health */}
        <Card title="App Health">
          <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
            <span className="inline-block h-2 w-2 rounded-full bg-green-500" />
            All systems operational
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
