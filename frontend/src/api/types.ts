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

/** Brief user reference (assigned agent, author, etc.) */
export interface UserBrief {
  id: string;
  email: string;
  display_name: string;
}

export type TicketStatus =
  | "open"
  | "assigned"
  | "in_progress"
  | "resolved"
  | "closed";

export type TicketPriority = "low" | "medium" | "high" | "critical";

/** Ticket model matching backend TicketResponse */
export interface Ticket {
  id: string;
  customer_email: string;
  customer_name: string;
  subject: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  assigned_agent_id: string | null;
  assigned_agent: UserBrief | null;
  attachment_paths: string[] | null;
  sla_deadline_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
}

/** GET /api/tickets and /api/queue */
export interface TicketListResponse {
  tickets: Ticket[];
  count: number;
}

/** Ticket comment matching backend TicketCommentResponse */
export interface TicketComment {
  id: string;
  ticket_id: string;
  author_id: string;
  body: string;
  is_internal: boolean;
  attachment_paths: string[] | null;
  created_at: string;
}

/** Ticket event matching backend TicketEventResponse */
export interface TicketEvent {
  id: string;
  ticket_id: string;
  actor_id: string | null;
  from_status: string | null;
  to_status: string;
  notes: string | null;
  created_at: string;
}

/** GET /api/tickets/{id} */
export interface TicketDetailResponse {
  ticket: Ticket;
  comments: TicketComment[];
  events: TicketEvent[];
}

/** GET /api/admin/reports */
export interface AdminReportResponse {
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  by_agent: Record<string, number>;
}

/** SSE event from GET /api/sse/tickets */
export interface SseEvent {
  type: "ticket_created" | "ticket_updated" | "comment_added";
  ticket_id: string;
  [key: string]: unknown;
}
