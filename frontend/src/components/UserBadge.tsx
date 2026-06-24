import type { User } from "../api/types";

interface UserBadgeProps {
  user: User;
}

export function UserBadge({ user }: UserBadgeProps) {
  const initial = user.display_name.charAt(0).toUpperCase();

  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-400">
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-xs font-medium text-blue-700 dark:bg-blue-900 dark:text-blue-300">
        {initial}
      </span>
      {user.display_name}
    </span>
  );
}
