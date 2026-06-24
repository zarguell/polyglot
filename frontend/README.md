# Polyglot React Frontend

React + Vite + TypeScript frontend for the Polyglot boilerplate.

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Dev server runs at `http://localhost:5173` with API proxy to `http://localhost:8000`.

## Commands

| Command | Purpose |
|---|---|
| `npm run dev` | Start Vite dev server (port 5173) |
| `npm run build` | Type-check + production build to `../app/static/react/` |
| `npm run preview` | Preview production build locally |
| `npm run typecheck` | Run TypeScript type-checking only |

## Architecture

### Stack
- **React 18** — UI library
- **Vite 5** — Build tool and dev server
- **TypeScript 5** — Strict mode type checking
- **React Router v7** — Client-side routing
- **@tanstack/react-query v5** — Server state management
- **Tailwind CSS v4** — Utility-first CSS with design tokens

### Auth Flow
1. App loads → `AuthGuard` checks `GET /api/me`
2. If 200 (authenticated) → redirect to `/dashboard`
3. If 401 (unauthenticated) → redirect to `/login`
4. Login page redirects to backend `/login` for OIDC (or dev login form)
5. After OIDC callback, browser lands at `/` with session cookie → `AuthGuard` detects user → redirects to `/dashboard`

### API Client (`src/api/client.ts`)
- Uses native `fetch` (no axios dependency)
- All requests include `credentials: 'same-origin'` for session cookie auth
- Automatic CSRF token handling via `X-CSRFToken` header
- Retries on CSRF 403 with token bootstrap from backend template

### Proxy Configuration
Vite dev server proxies to FastAPI backend:
- `/api/*` → `http://localhost:8000`
- `/login`, `/auth/*`, `/logout` → `http://localhost:8000`
- `/healthz`, `/readyz` → `http://localhost:8000`

### Production Build
```bash
npm run build
```
Output goes to `app/static/react/` where FastAPI serves static files at `/static/react/`.

## Design Tokens

Design tokens are sourced from `../DESIGN_TOKENS.json` (repo root):
- Primary: `#2563eb` (blue-600)
- Surface: `#ffffff` / `#f9fafb`
- Border: `#e5e7eb` (gray-200)
- Text: `#111827` (gray-900) / `#6b7280` (gray-500)
- Font: system-ui, -apple-system, sans-serif
- Border radius: 0.5rem (rounded-lg)
- Dark mode: Supported via `prefers-color-scheme`

Tokens are applied via CSS custom properties in `src/styles/index.css` and Tailwind `@theme`.
