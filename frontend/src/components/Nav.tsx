import { NavLink } from "react-router-dom";
import { EnvBadge } from "./EnvBadge";
import { UserBadge } from "./UserBadge";
import { Button } from "./Button";
import type { User } from "../api/types";

interface NavProps {
  user: User | null;
  onLogout: () => void;
}

const linkBase =
  "text-sm transition-colors";
const linkInactive =
  "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200";
const linkActive =
  "text-gray-900 dark:text-gray-100 font-medium";

function navLinkClass({ isActive }: { isActive: boolean }) {
  return `${linkBase} ${isActive ? linkActive : linkInactive}`;
}

export function Nav({ user, onLogout }: NavProps) {
  return (
    <nav className="border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-6">
            <NavLink
              to="/"
              className="text-lg font-semibold text-gray-900 dark:text-gray-100"
            >
              Polyglot
            </NavLink>
            {user ? (
              <>
                <NavLink to="/" className={navLinkClass}>
                  Tickets
                </NavLink>
                <NavLink to="/queue" className={navLinkClass}>
                  Queue
                </NavLink>
                {user.is_admin && (
                  <NavLink to="/admin" className={navLinkClass}>
                    Admin
                  </NavLink>
                )}
                <NavLink to="/dashboard" className={navLinkClass}>
                  Dashboard
                </NavLink>
              </>
            ) : (
              <NavLink to="/tickets/new" className={navLinkClass}>
                Submit Ticket
              </NavLink>
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
              <>
                <NavLink to="/tickets/new">
                  <Button variant="secondary">Submit Ticket</Button>
                </NavLink>
                <NavLink to="/login">
                  <Button>Login</Button>
                </NavLink>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
