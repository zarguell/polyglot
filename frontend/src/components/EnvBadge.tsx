interface EnvBadgeProps {
  environment?: string;
}

const envColors: Record<string, string> = {
  production:
    "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  staging:
    "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
  local:
    "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  dev: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
};

export function EnvBadge({ environment = "local" }: EnvBadgeProps) {
  const colorClass =
    envColors[environment] ?? envColors.local;

  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${colorClass}`}
    >
      {environment}
    </span>
  );
}
