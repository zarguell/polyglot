import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AppShell } from "../components/AppShell";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { Button } from "../components/Button";
import { StatusBadge, PriorityBadge } from "../components/Badges";
import { useSSE } from "../hooks/useSSE";
import { api } from "../api/client";
import type {
  User,
  TicketListResponse,
  Ticket,
  TicketPriority,
} from "../api/types";

interface AgentQueuePageProps {
  user: User;
}

const PRIORITY_ORDER: Record<TicketPriority, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

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

export function AgentQueuePage({ user }: AgentQueuePageProps) {
  const queryClient = useQueryClient();

  const queueQuery = useQuery<TicketListResponse>({
    queryKey: ["queue"],
    queryFn: () => api.get<TicketListResponse>("/queue"),
  });

  const claimMutation = useMutation({
    mutationFn: (ticketId: string) =>
      api.patch<Ticket>(`/tickets/${ticketId}`, {
        status: "assigned",
        assigned_agent_id: user.id,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["queue"] });
      void queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
  });

  useSSE({
    onEvent: (event) => {
      if (event.type === "ticket_created") {
        void queryClient.invalidateQueries({ queryKey: ["queue"] });
      }
    },
  });

  async function handleLogout() {
    try {
      await api.post("/logout");
    } catch {
      /* fall through */
    }
    window.location.href = "/login";
  }

  const tickets = queueQuery.data?.tickets ?? [];
  const sorted = useMemo(
    () =>
      [...tickets].sort((a, b) => {
        const po = PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
        if (po !== 0) return po;
        return (
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        );
      }),
    [tickets],
  );

  return (
    <AppShell user={user} onLogout={handleLogout}>
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Agent Queue
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Unassigned tickets waiting to be claimed.
          </p>
        </div>

        <Card className="p-0">
          {queueQuery.isLoading ? (
            <div className="px-6 py-12 text-center text-sm text-gray-500">
              Loading queue…
            </div>
          ) : queueQuery.isError ? (
            <div className="px-6 py-12 text-center text-sm text-red-600">
              Failed to load queue.
            </div>
          ) : sorted.length === 0 ? (
            <EmptyState
              title="Queue is empty"
              description="All caught up! New tickets will appear here automatically."
            />
          ) : (
            <ul className="divide-y divide-gray-100 dark:divide-gray-800">
              {sorted.map((t: Ticket) => (
                <li
                  key={t.id}
                  className="flex flex-wrap items-center justify-between gap-3 px-6 py-4"
                >
                  <div className="min-w-0 flex-1">
                    <Link
                      to={`/tickets/${t.id}`}
                      className="block truncate text-sm font-medium text-gray-900 hover:text-blue-600 hover:underline dark:text-gray-100"
                    >
                      {t.subject}
                    </Link>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <PriorityBadge priority={t.priority} />
                      <StatusBadge status={t.status} />
                      <span className="text-xs text-gray-500">
                        {t.customer_name}
                      </span>
                      <span className="text-xs text-gray-400">
                        {formatDate(t.created_at)}
                      </span>
                    </div>
                  </div>
                  <Button
                    disabled={
                      claimMutation.isPending &&
                      claimMutation.variables === t.id
                    }
                    onClick={() => claimMutation.mutate(t.id)}
                  >
                    {claimMutation.isPending && claimMutation.variables === t.id
                      ? "Claiming…"
                      : "Claim"}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
