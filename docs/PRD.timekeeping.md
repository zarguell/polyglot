# PRD: Internal Timekeeping & Leave Management

> Use this PRD to guide an AI agent in building within the Polyglot scaffold.

## Problem Statement

The company needs an internal timekeeping system for hourly employees to submit
timecards, managers to approve them, and timekeepers to finalize payroll records.
Employees also need to request leave (PTO, sick, holiday) and have it approved
through a multi-step workflow. Currently this is done via spreadsheets and email.

## Users / Personas

- **Employee:** Submits timecards weekly, requests leave, views own balance
- **Manager:** Approves/rejects timecards and leave for direct reports
- **Timekeeper:** Finalizes timecards after approval, runs payroll reports,
  adjusts leave balances, configures accrual policies
- **Admin:** Manages users, org hierarchy (who reports to whom), system config

## Core Entities

**Employee**
- id, user_id (FK to auth User), manager_id (nullable FK to self), department,
  hire_date, employment_type (hourly/salary), tenure_policy_id

**Timecard**
- id, employee_id, week_ending (date), status (draft → submitted → approved → finalized),
  submitted_at, approved_at, finalized_at, notes

**TimecardEntry**
- id, timecard_id, date, hours (decimal), project_code, description

**LeaveRequest**
- id, employee_id, leave_type (pto/sick/holiday/unpaid), start_date, end_date,
  hours_requested, status (requested → approved → taken → cancelled),
  approver_notes, reviewed_by_id, reviewed_at

**LeaveBalance**
- id, employee_id, leave_type, year, total_hours, used_hours, accrued_hours

**AccrualPolicy**
- id, name, leave_type, accrual_rate_hours_per_period, period_days,
  max_balance_hours, tenure_multiplier (JSON: {years: multiplier, ...})

**ApprovalAction**
- id, target_type (timecard/leave), target_id, actor_id, action (approve/reject),
  notes, created_at

## Workflows

### Timecard
1. Employee fills timecard entries for the past week (Mon–Sun)
2. Employee submits → status = "submitted"
3. Manager reviews → approve (status = "approved") or reject (back to "draft")
4. Timekeeper finalizes → status = "finalized" (locked, no further edits)

### Leave Request
1. Employee submits leave request with dates and type
2. System checks: sufficient balance? → if no, warn but allow submission
3. Manager approves or rejects
4. If approved → leave balance deducted, status = "approved"
5. Employee takes leave → status = "taken" (on start date, via cron)
6. Employee cancels → status = "cancelled", balance restored

### Leave Accrual (weekly cron)
1. Procrastinate job runs every Monday 2 AM
2. For each active employee, accrue leave hours based on AccrualPolicy
3. Apply tenure multiplier based on hire_date
4. Cap at max_balance_hours

## Permissions (RBAC)

Use the boilerplate's `require_permission(resource, action)` factory:

| Resource | Action | Employee | Manager | Timekeeper | Admin |
|----------|--------|----------|---------|------------|-------|
| timecards | create | own only | — | — | — |
| timecards | read | own only | team only | all | all |
| timecards | update | own (draft only) | — | all (finalize) | all |
| timecards | approve | — | team pending | — | — |
| timecards | finalize | — | — | approved only | — |
| leave | create | own only | — | — | — |
| leave | read | own only | team only | all | all |
| leave | approve | — | team pending | — | — |
| leave | adjust_balance | — | — | all | all |
| employees | read | self | team | all | all |
| employees | manage | — | — | — | all |
| accrual_policies | manage | — | — | — | all |

*Manager scope = employees where employee.manager_id == current_user.id*

## Pages / Screens

- `/dashboard` — My pending approvals, upcoming leave, this week's hours
- `/timecards` — My timecards list (status filter, week picker)
- `/timecards/new` — Weekly timecard entry form (5 or 7 day rows)
- `/timecards/{id}` — Timecard detail with entry table, approve/reject buttons
- `/timecards/pending` — Manager view: team timecards awaiting approval
- `/timecards/finalize` — Timekeeper view: all approved timecards ready to finalize
- `/leave` — My leave requests, balance display
- `/leave/new` — Leave request form (type, dates, reason)
- `/leave/pending` — Manager view: team leave requests awaiting approval
- `/reports/payroll` — Timekeeper view: CSV export of finalized hours by date range
- `/admin/employees` — Manage users, org hierarchy (Admin only)
- `/admin/policies` — Accrual policy config (Admin only)

## Reports (via reporting_exports component)

- **Payroll CSV**: Employee, hours, pay_code, date range — finalized timecards
- **Team Availability**: Next 2 weeks showing who's on leave
- **Leave Balance Report**: All employees, all leave types, used/remaining
- **Monthly Accrual Summary**: Hours accrued, used, forfeited per policy

## Notifications

- **Email** (via SMTP component):
  - Timecard submitted → manager notified
  - Timecard approved/rejected → employee notified
  - Leave request submitted → manager notified
  - Leave approved/rejected → employee notified
  - Low leave balance warning (< 5 days remaining)
- **Webhook** (via outbound_webhooks component, optional):
  - Leave starting tomorrow → Slack #team-availability
  - Timecard finalized → payroll system webhook

## Cron Tasks (Procrastinate)

| Task | Schedule | Description |
|------|----------|-------------|
| `leave.accrue_hours` | Every Monday 2 AM | Accrue PTO/sick per AccrualPolicy |
| `leave.mark_taken` | Daily 6 AM | Mark approved leave as "taken" when start_date arrives |
| `leave.auto_cancel_expired` | Daily 6 AM | Cancel unapproved leave requests older than 14 days |
| `timekeeping.remind_submission` | Every Tuesday 8 AM | Remind employees who haven't submitted last week's timecard |

## Integrations

- **Slack** (via outbound_webhooks): Team availability notifications
- **Payroll export** (via reporting_exports): CSV for payroll provider

## Optional Components to Activate

```
make activate-component COMPONENT=smtp
make activate-component COMPONENT=fsm_workflows
make activate-component COMPONENT=reporting_exports
make activate-component COMPONENT=outbound_webhooks
make activate-component COMPONENT=inbound_webhooks
```

## Non-Functional Requirements

- Timekeepers must not be able to edit finalized timecards (immutable records)
- Manager can only see and act on their direct reports (org hierarchy scoping)
- All approval/rejection actions audit-logged
- CSRF protected on all forms
- Timecard entry supports decimal hours (e.g., 7.5)
- Leave balance calculations must be idempotent (cron can rerun safely)
- Page loads under 2s for list views with up to 500 timecards
