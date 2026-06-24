import { useState } from "react";
import { Button } from "../components/Button";
import { AppShell } from "../components/AppShell";

export function LoginPage() {
  const [devEmail, setDevEmail] = useState("");
  const [devName, setDevName] = useState("");

  function handleOidcLogin() {
    window.location.href = "/login";
  }

  async function handleDevLogin(e: React.FormEvent) {
    e.preventDefault();
    // Dev login: redirect to backend /login which shows dev form,
    // OR if already on dev login via backend, use the backend POST
    // For React SPA: redirect to backend /login (which shows dev form in dev mode)
    window.location.href = "/login";
    // Note: The backend /login endpoint renders dev_login.html in dev mode.
    // We redirect there so the backend handles the form POST with CSRF protection.
  }

  return (
    <AppShell user={null} onLogout={() => {}}>
      <div className="mx-auto max-w-sm px-4 py-16">
        {/* Dev Mode Warning Banner */}
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-center text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          DEV MODE
        </div>

        <h1 className="mb-6 text-center text-xl font-semibold text-gray-900 dark:text-gray-100">
          Sign In
        </h1>

        <div className="space-y-4">
          <Button onClick={handleOidcLogin} className="w-full">
            Sign in with SSO
          </Button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-gray-600" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="bg-white px-2 text-gray-500 dark:bg-gray-900 dark:text-gray-400">
                or
              </span>
            </div>
          </div>

          <form onSubmit={handleDevLogin} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Email
              </label>
              <input
                type="email"
                name="email"
                id="email"
                required
                value={devEmail}
                onChange={(e) => setDevEmail(e.target.value)}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              />
            </div>
            <div>
              <label
                htmlFor="display_name"
                className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Display Name
              </label>
              <input
                type="text"
                name="display_name"
                id="display_name"
                value={devName}
                onChange={(e) => setDevName(e.target.value)}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
              />
            </div>
            <Button type="submit" className="w-full">
              Sign in (Dev)
            </Button>
          </form>
        </div>
      </div>
    </AppShell>
  );
}
