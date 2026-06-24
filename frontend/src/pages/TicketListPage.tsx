import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "../components/AppShell";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { Button } from "../components/Button";
import { StatusBadge, PriorityBadge } from "../components/Badges";
import { useSSE } from "../hooks/useSSE";
import { api } from "../api/client";
import type { User, TicketListResponse, Ticket, TicketPriority } from "../api/types";

interface TicketListPageProps {
  user: User;
}

const PRIORITY_ORDER: Record<TicketPriority, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

function truncateId(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatSla(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const now = Date.now();
  const ms = d.getTime() - now;
  const hours = Math.round(ms / 3_600_000);
  if (hours < 0) return `Overdue ${Math.abs(hours)}h`;
  if (hours < 24) return `${hours}h left`;
  return `${Math.round(hours / 24)}d left`;
}

export function TicketListPage({ user }: TicketListPageProps) {
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();

  const ticketsQuery = useQuery<TicketListResponse>({
    queryKey: ["tickets"],
    queryFn: () => api.get<TicketListResponse>("/tickets"),
  });

  const searchQuery = useQuery<TicketListResponse>({
    queryKey: ["tickets", "search", search],
    queryFn: () =>
      api.get<TicketListResponse>(
        `/tickets/search?q=${encodeURIComponent(search)}`,
      ),
    enabled: search.trim().length > 0,
  });

  useSSE({
    onEvent: (event) => {
      if (event.type === "ticket_created" || event.type === "ticket_updated") {
        void queryClient.invalidateQueries({ queryKey: ["tickets"] });
      }
    },
  });

  async function handleLogout() {
    try {
      await api.post("/logout");
    } catch {
      /* fall through to reload */
    }
    window.location.href = "/login";
  }

  const activeQuery = search.trim() ? searchQuery : ticketsQuery;
  const tickets = activeQuery.data?.tickets ?? [];
  const isLoading = activeQuery.isLoading;
  const isError = activeQuery.isError;

  const sorted = useMemo(() => {
    return [...tickets].sort((a, b) => {
      const po = PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
      if (po !== 0) return po;
      return (
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
    });
  }, [tickets]);

  return (
    <AppShell user={user} onLogout={handleLogout}>
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              Tickets
            </h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {ticketsQuery.data?.count ?? 0} total
            </p>
          </div>
          <Link to="/tickets/new">
            <Button>New Ticket</Button>
          </Link>
        </div>

        <div className="mb-4">
          <input
            type="search"
            placeholder="Search tickets by subject, customer, or description…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          />
        </div>

        <Card className="p-0">
          {isLoading ? (
            <div className="px-6 py-12 text-center text-sm text-gray-500">
              Loading tickets…
            </div>
          ) : isError ? (
            <div className="px-6 py-12 text-center text-sm text-red-600">
              Failed to load tickets.
            </div>
          ) : sorted.length === 0 ? (
            <EmptyState
              title={search.trim() ? "No matching tickets" : "No tickets yet"}
              description={
                search.trim()
                  ? "Try a different search term."
                  : "New support requests will appear here."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    {["ID", "Subject", "Customer", "Status", "Priority", "Agent", "Created", "SLA"].map(
                      (h) => (
                        <th
                          key={h}
                          className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400"
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white dark:divide-gray-800 dark:bg-gray-900">
                  {sorted.map((t: Ticket) => (
                    <tr
                      key={t.id}
                      className="hover:bg-gray-50 dark:hover:bg-gray-800"
                    >
                      <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-gray-500">
                        <Link
                          to={`/tickets/${t.id}`}
                          className="hover:text-blue-600"
                        >
                          {truncateId(t.id)}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-gray-100">
                        <Link
                          to={`/tickets/${t.id}`}
                          className="hover:text-blue-600 hover:underline"
                        >
                          {t.subject}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                        {t.customer_name}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={t.status} />
                      </td>
                      <td className="px-4 py-3">
                        <PriorityBadge priority={t.priority} />
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                        {t.assigned_agent?.display_name ?? "Unassigned"}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-500">
                        {formatDate(t.created_at)}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-500">
                        {formatSla(t.sla_deadline_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
