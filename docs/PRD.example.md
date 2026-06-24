# PRD.example.md — Example: Internal Issue Tracker

> This is an example Product Requirements Document. Replace with your own PRD to
> guide an AI agent in building your application within the Polyglot scaffold.

## Problem Statement

The engineering team needs a lightweight issue tracker for tracking bugs and feature requests during internal sprints. Current tools are either too heavy (Jira) or not self-hosted (GitHub Issues).

## Users / Personas

- **Engineer:** Reports bugs, tracks assigned work
- **Lead:** Triages issues, assigns work, reviews reports
- **Admin:** Configures workflows, manages users

## Core Entities

- **Issue:** id, title, description, status, priority, assignee, reporter, labels, created_at, updated_at
- **Comment:** id, issue_id, author, body, created_at
- **Label:** name, color

## Workflows

1. Engineer creates issue → status = "Open"
2. Lead triages → status = "Triaged", assignee set
3. Engineer starts work → status = "In Progress"
4. Engineer resolves → status = "Resolved"
5. Lead verifies → status = "Closed" (or reopens)

## Permissions

- Admin: full CRUD, user management, label management
- Lead: triage, assign, close/reopen any issue
- Engineer: create issues, comment, edit own issues
- Viewer: read-only

## Pages / Screens

- `/issues` — list view with filters (status, priority, assignee, label)
- `/issues/new` — creation form
- `/issues/{id}` — detail view with comments
- `/issues/{id}/edit` — edit form
- `/users` — admin user list
- `/reports` — simple sprint burndown

## Reports

- Open issues by priority
- Issues closed this sprint
- Burndown (optional, weekly cron-generated)

## Notifications

- Email on issue assignment (via SMTP template if enabled)
- Email on status change (if SMTP active)

## Integrations

- Webhook on issue create/update for Slack/Teams (via outbound_webhooks template)

## Non-Functional Requirements

- Every status change audit-logged
- CSRF protected
- At most 2s page load for list views
- Mobile-responsive (basic)
