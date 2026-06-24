import type { ReactNode } from "react";
import { Nav } from "./Nav";
import type { User } from "../api/types";

interface AppShellProps {
  user: User | null;
  onLogout: () => void;
  children: ReactNode;
}

export function AppShell({ user, onLogout, children }: AppShellProps) {
  return (
    <div className="flex min-h-full flex-col">
      <Nav user={user} onLogout={onLogout} />
      <main className="flex-1">{children}</main>
    </div>
  );
}
