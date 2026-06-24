import { EnvBadge } from "./EnvBadge";
import { UserBadge } from "./UserBadge";
import { Button } from "./Button";
import type { User } from "../api/types";

interface NavProps {
  user: User | null;
  onLogout: () => void;
}

export function Nav({ user, onLogout }: NavProps) {
  return (
    <nav className="border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-4">
            <a href="/" className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Polyglot
            </a>
            {user && (
              <a
                href="/dashboard"
                className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                Dashboard
              </a>
            )}
          </div>
          <div className="flex items-center gap-3">
            {user ? (
              <>
                <UserBadge user={user} />
                <EnvBadge environment="local" />
                <Button variant="ghost" onClick={onLogout}>
                  Logout
                </Button>
              </>
            ) : (
              <a href="/login">
                <Button>Login</Button>
              </a>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
