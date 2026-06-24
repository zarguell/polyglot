import { useState } from "react";
import { Link } from "react-router-dom";
import { AppShell } from "../components/AppShell";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { api } from "../api/client";
import type { Ticket, TicketPriority } from "../api/types";

const PRIORITIES: TicketPriority[] = ["low", "medium", "high", "critical"];

interface FieldProps {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}

function Field({ label, htmlFor, children }: FieldProps) {
  return (
    <div>
      <label
        htmlFor={htmlFor}
        className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
      >
        {label}
      </label>
      {children}
    </div>
  );
}

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100";

export function TicketFormPage() {
  const [customerEmail, setCustomerEmail] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("medium");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<Ticket | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const ticket = await api.post<Ticket>("/tickets", {
        customer_email: customerEmail,
        customer_name: customerName,
        subject,
        description,
        priority,
      });
      setCreated(ticket);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to submit ticket.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (created) {
    return (
      <AppShell user={null} onLogout={() => {}}>
        <div className="mx-auto max-w-lg px-4 py-16">
          <Card>
            <div className="text-center">
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
                <svg
                  className="h-6 w-6 text-green-600 dark:text-green-300"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                Ticket Submitted
              </h2>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Your reference ID is
              </p>
              <p className="mt-1 font-mono text-sm font-medium text-blue-600">
                {created.id}
              </p>
              <div className="mt-6 flex justify-center gap-3">
                <Button onClick={() => window.location.reload()}>
                  Submit Another
                </Button>
                <Link to="/">
                  <Button variant="secondary">View Tickets</Button>
                </Link>
              </div>
            </div>
          </Card>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell user={null} onLogout={() => {}}>
      <div className="mx-auto max-w-lg px-4 py-12">
        <h1 className="mb-1 text-2xl font-bold text-gray-900 dark:text-gray-100">
          Submit a Support Request
        </h1>
        <p className="mb-6 text-sm text-gray-500 dark:text-gray-400">
          Tell us what you need and an agent will get back to you.
        </p>

        <Card>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Field label="Your Name" htmlFor="customer_name">
              <input
                id="customer_name"
                type="text"
                required
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                className={inputClass}
                placeholder="Jane Doe"
              />
            </Field>

            <Field label="Email Address" htmlFor="customer_email">
              <input
                id="customer_email"
                type="email"
                required
                value={customerEmail}
                onChange={(e) => setCustomerEmail(e.target.value)}
                className={inputClass}
                placeholder="jane@example.com"
              />
            </Field>

            <Field label="Subject" htmlFor="subject">
              <input
                id="subject"
                type="text"
                required
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className={inputClass}
                placeholder="Brief summary of your issue"
              />
            </Field>

            <Field label="Description" htmlFor="description">
              <textarea
                id="description"
                required
                rows={5}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className={inputClass}
                placeholder="Describe your issue in detail…"
              />
            </Field>

            <Field label="Priority" htmlFor="priority">
              <select
                id="priority"
                value={priority}
                onChange={(e) => setPriority(e.target.value as TicketPriority)}
                className={inputClass}
              >
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </option>
                ))}
              </select>
            </Field>

            {error && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
                {error}
              </p>
            )}

            <Button type="submit" disabled={submitting} className="w-full">
              {submitting ? "Submitting…" : "Submit Ticket"}
            </Button>
          </form>
        </Card>
      </div>
    </AppShell>
  );
}
