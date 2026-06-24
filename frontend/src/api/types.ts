/** User model matching backend app/models/user.py */
export interface User {
  id: string;
  email: string;
  display_name: string;
  auth_provider: string;
  is_admin: boolean;
  last_login_at: string | null;
}

/** GET /healthz response */
export interface HealthResponse {
  status: string;
}

/** GET /readyz response */
export interface ReadyResponse {
  status: string;
  database: string;
}

/** Audit log entry (app/models/audit_log.py) */
export interface AuditLog {
  id: string;
  actor_user_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  ip_address: string | null;
  request_id: string | null;
  created_at: string;
}

/** Installed component (app/models/installed_component.py) */
export interface InstalledComponent {
  id: string;
  name: string;
  version: string;
  activated_at: string;
}

/** RBAC Role (app/schemas/role.py) */
export interface Role {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
}

/** Permission (app/schemas/role.py) */
export interface Permission {
  id: string;
  resource: string;
  action: string;
  description: string | null;
}

/** User roles response */
export interface UserRoles {
  user_id: string;
  roles: Role[];
  permission_count: number;
}

/** Generic API error from the backend */
export interface ApiError {
  detail: string;
  status_code: number;
}
