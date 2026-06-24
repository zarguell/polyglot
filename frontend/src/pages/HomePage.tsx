import { AppShell } from "../components/AppShell";
import { Button } from "../components/Button";
import { Card } from "../components/Card";

const FEATURES = [
  {
    title: "Secure by Default",
    description:
      "OIDC SSO, CSP, CSRF, trusted hosts, secure cookies — all wired.",
  },
  {
    title: "Postgres Native",
    description:
      "Data, tasks, audit — all in Postgres. No extra infra to run.",
  },
  {
    title: "Component System",
    description:
      "Copy-on-activate templates for SMTP, Stripe, Webhooks, and more.",
  },
];

export function HomePage() {
  return (
    <AppShell user={null} onLogout={() => {}}>
      <div className="mx-auto max-w-4xl px-4 py-16 text-center sm:py-24">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 dark:text-gray-100 sm:text-5xl">
          Polyglot
        </h1>
        <p className="mt-4 text-lg text-gray-500 dark:text-gray-400">
          AI-native secure application boilerplate
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <a href="/login">
            <Button>Sign in</Button>
          </a>
        </div>
        <div className="mt-12 grid grid-cols-1 gap-6 text-left sm:grid-cols-3">
          {FEATURES.map((f) => (
            <Card key={f.title}>
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">
                {f.title}
              </h3>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                {f.description}
              </p>
            </Card>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
