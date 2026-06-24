import { useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { AppShell } from "../components/AppShell";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { StatusBadge, PriorityBadge } from "../components/Badges";
import { api, ApiClientError } from "../api/client";
import type {
  User,
  Ticket,
  TicketDetailResponse,
  TicketComment,
  TicketStatus,
} from "../api/types";

interface TicketDetailPageProps {
  user: User;
}

interface Transition {
  label: string;
  patch: Partial<Ticket>;
  variant?: "primary" | "secondary" | "danger";
}

function transitionsFor(
  status: TicketStatus,
  currentUserId: string,
): Transition[] {
  switch (status) {
    case "open":
      return [
        {
          label: "Claim",
          patch: { status: "assigned", assigned_agent_id: currentUserId },
          variant: "primary",
        },
        { label: "Close", patch: { status: "closed" }, variant: "secondary" },
      ];
    case "assigned":
      return [
        { label: "Start Progress", patch: { status: "in_progress" } },
        { label: "Reopen", patch: { status: "open" }, variant: "secondary" },
      ];
    case "in_progress":
      return [
        { label: "Resolve", patch: { status: "resolved" } },
        {
          label: "Reassign",
          patch: { status: "open", assigned_agent_id: null },
          variant: "secondary",
        },
      ];
    case "resolved":
      return [
        { label: "Close", patch: { status: "closed" } },
        { label: "Reopen", patch: { status: "open" }, variant: "secondary" },
      ];
    case "closed":
      return [{ label: "Reopen", patch: { status: "open" } }];
    default:
      return [];
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function attachmentKey(path: string): string {
  const parts = path.split("/");
  return parts[parts.length - 1] ?? path;
}

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100";

export function TicketDetailPage({ user }: TicketDetailPageProps) {
  const { id: ticketId } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [commentBody, setCommentBody] = useState("");
  const [isInternal, setIsInternal] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const detailQuery = useQuery<TicketDetailResponse>({
    queryKey: ["ticket", ticketId],
    queryFn: () => api.get<TicketDetailResponse>(`/tickets/${ticketId}`),
    enabled: !!ticketId,
  });

  const patchMutation = useMutation({
    mutationFn: (patch: Partial<Ticket>) =>
      api.patch<Ticket>(`/tickets/${ticketId}`, patch),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ticket", ticketId] });
      void queryClient.invalidateQueries({ queryKey: ["tickets"] });
    },
  });

  const commentMutation = useMutation({
    mutationFn: (vars: { body: string; is_internal: boolean }) =>
      api.post<TicketComment>(`/tickets/${ticketId}/comments`, vars),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ticket", ticketId] });
      setCommentBody("");
      setIsInternal(false);
    },
  });

  const ticket = detailQuery.data?.ticket;
  const comments = detailQuery.data?.comments ?? [];
  const events = detailQuery.data?.events ?? [];

  async function handleUpload(file: File) {
    setUploadError(null);
    const formData = new FormData();
    formData.append("file", file);
    const meta = document.querySelector<HTMLMetaElement>(
      'meta[name="csrf-token"]',
    );
    const res = await fetch(`/api/tickets/${ticketId}/attachments`, {
      method: "POST",
      credentials: "same-origin",
      headers: meta?.content ? { "X-CSRFToken": meta.content } : {},
      body: formData,
    });
    if (!res.ok) {
      const err = (await res.json().catch(() => ({ detail: res.statusText }))) as {
        detail?: string;
      };
      setUploadError(err.detail ?? "Upload failed");
      return;
    }
    void queryClient.invalidateQueries({ queryKey: ["ticket", ticketId] });
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) void handleUpload(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleLogout() {
    try {
      await api.post("/logout");
    } catch {
      /* fall through */
    }
    window.location.href = "/login";
  }

  if (detailQuery.isLoading) {
    return (
      <AppShell user={user} onLogout={handleLogout}>
        <div className="px-4 py-12 text-center text-sm text-gray-500">
          Loading ticket…
        </div>
      </AppShell>
    );
  }

  if (detailQuery.isError || !ticket) {
    return (
      <AppShell user={user} onLogout={handleLogout}>
        <div className="mx-auto max-w-3xl px-4 py-12">
          <Card>
            <p className="text-center text-sm text-red-600">
              {detailQuery.error instanceof ApiClientError &&
              detailQuery.error.status === 404
                ? "Ticket not found."
                : "Failed to load ticket."}
            </p>
            <div className="mt-4 text-center">
              <Link to="/">
                <Button variant="secondary">Back to Tickets</Button>
              </Link>
            </div>
          </Card>
        </div>
      </AppShell>
    );
  }

  const transitions = transitionsFor(ticket.status, user.id);

  return (
    <AppShell user={user} onLogout={handleLogout}>
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-4">
          <Link
            to="/"
            className="text-sm text-gray-500 hover:text-blue-600 dark:text-gray-400"
          >
            ← Back to tickets
          </Link>
        </div>

        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {ticket.subject}
            </h1>
            <p className="mt-1 font-mono text-xs text-gray-400">{ticket.id}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <StatusBadge status={ticket.status} />
              <PriorityBadge priority={ticket.priority} />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {transitions.map((t) => (
              <Button
                key={t.label}
                variant={t.variant ?? "primary"}
                disabled={patchMutation.isPending}
                onClick={() => patchMutation.mutate(t.patch)}
              >
                {t.label}
              </Button>
            ))}
          </div>
        </div>

        {patchMutation.isError && (
          <p className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
            Failed to update ticket.
          </p>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="space-y-6 lg:col-span-2">
            <Card title="Description">
              <p className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
                {ticket.description}
              </p>
            </Card>

            <Card title="Comments">
              <div className="space-y-4">
                {comments.length === 0 && (
                  <p className="text-sm text-gray-500">No comments yet.</p>
                )}
                {comments.map((c: TicketComment) => (
                  <div
                    key={c.id}
                    className="rounded-lg border border-gray-200 p-3 dark:border-gray-800"
                  >
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                        {formatDate(c.created_at)}
                      </span>
                      {c.is_internal && (
                        <span className="rounded bg-yellow-100 px-1.5 py-0.5 text-xs font-medium text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300">
                          Internal
                        </span>
                      )}
                    </div>
                    <p className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
                      {c.body}
                    </p>
                  </div>
                ))}
              </div>

              <form
                className="mt-4 space-y-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (commentBody.trim()) {
                    commentMutation.mutate({
                      body: commentBody.trim(),
                      is_internal: isInternal,
                    });
                  }
                }}
              >
                <textarea
                  rows={3}
                  value={commentBody}
                  onChange={(e) => setCommentBody(e.target.value)}
                  className={inputClass}
                  placeholder="Add a comment…"
                />
                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                    <input
                      type="checkbox"
                      checked={isInternal}
                      onChange={(e) => setIsInternal(e.target.checked)}
                      className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    Internal note
                  </label>
                  <Button type="submit" disabled={commentMutation.isPending}>
                    {commentMutation.isPending ? "Posting…" : "Add Comment"}
                  </Button>
                </div>
              </form>
            </Card>

            <Card title="Attachments">
              <div className="space-y-2">
                {(!ticket.attachment_paths ||
                  ticket.attachment_paths.length === 0) && (
                  <p className="text-sm text-gray-500">No attachments.</p>
                )}
                {ticket.attachment_paths?.map((path) => (
                  <a
                    key={path}
                    href={`/api/tickets/${ticket.id}/attachments/${encodeURIComponent(
                      attachmentKey(path),
                    )}`}
                    className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
                  >
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 10-5.656-5.656L5.05 11.293a6 6 0 108.486 8.486l5.414-5.414"
                      />
                    </svg>
                    {attachmentKey(path)}
                  </a>
                ))}
              </div>

              <div className="mt-4">
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={onFileChange}
                  className="hidden"
                />
                <Button
                  variant="secondary"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Upload File
                </Button>
                {uploadError && (
                  <p className="mt-2 text-sm text-red-600">{uploadError}</p>
                )}
              </div>
            </Card>
          </div>

          <div className="space-y-6">
            <Card title="Details">
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">Customer</dt>
                  <dd className="font-medium text-gray-900 dark:text-gray-100">
                    {ticket.customer_name}
                  </dd>
                  <dd className="text-xs text-gray-500">{ticket.customer_email}</dd>
                </div>
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">Agent</dt>
                  <dd className="font-medium text-gray-900 dark:text-gray-100">
                    {ticket.assigned_agent?.display_name ?? "Unassigned"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">
                    SLA Deadline
                  </dt>
                  <dd className="font-medium text-gray-900 dark:text-gray-100">
                    {formatDate(ticket.sla_deadline_at)}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">Created</dt>
                  <dd className="text-gray-900 dark:text-gray-100">
                    {formatDate(ticket.created_at)}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">Updated</dt>
                  <dd className="text-gray-900 dark:text-gray-100">
                    {formatDate(ticket.updated_at)}
                  </dd>
                </div>
              </dl>
            </Card>

            <Card title="Activity">
              <ol className="relative space-y-4 border-l border-gray-200 pl-4 dark:border-gray-800">
                {events.length === 0 && (
                  <li className="text-sm text-gray-500">No activity yet.</li>
                )}
                {events.map((ev) => (
                  <li key={ev.id} className="ml-2">
                    <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-blue-500" />
                    <p className="text-sm text-gray-700 dark:text-gray-300">
                      {ev.from_status ? (
                        <>
                          <span className="font-medium">{ev.from_status}</span>
                          {" → "}
                          <span className="font-medium">{ev.to_status}</span>
                        </>
                      ) : (
                        <span className="font-medium">Created as {ev.to_status}</span>
                      )}
                    </p>
                    {ev.notes && (
                      <p className="mt-0.5 text-xs text-gray-500">{ev.notes}</p>
                    )}
                    <p className="mt-0.5 text-xs text-gray-400">
                      {formatDate(ev.created_at)}
                    </p>
                  </li>
                ))}
              </ol>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
