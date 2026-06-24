import { useEffect, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api } from "../api/client";
import type { User } from "../api/types";

interface AuthGuardProps {
  children: (user: User) => ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const location = useLocation();

  useEffect(() => {
    let cancelled = false;
    api
      .get<User>("/me")
      .then((u) => {
        if (!cancelled) {
          // Bootstrap CSRF token for future POST requests
          api.bootstrapCsrfToken().catch(() => {});
          setUser(u);
          setLoading(false);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          if (e instanceof Error && e.message.includes("401")) {
            setError(true);
          } else {
            setError(true);
          }
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-sm text-gray-500">Loading...</div>
      </div>
    );
  }

  if (error || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children(user)}</>;
}
