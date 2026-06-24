# DESIGN.md — Polyglot Design System

This file controls all visual design decisions. AI agents must consult this before generating UI.

## Brand

- **App Name:** Polyglot
- **Tagline:** AI-native secure application boilerplate
- **Tone:** Minimal, professional, accessible

## Color Palette

| Token | Value | Usage |
|---|---|---|
| Primary | `#2563eb` (blue-600) | Buttons, links, focus states |
| Primary hover | `#1d4ed8` (blue-700) | Button hover |
| Surface | `#ffffff` | Card/page backgrounds |
| Surface secondary | `#f9fafb` (gray-50) | Alternate rows, subtle backgrounds |
| Border | `#e5e7eb` (gray-200) | Card borders, dividers |
| Text | `#111827` (gray-900) | Headings, body |
| Text secondary | `#6b7280` (gray-500) | Labels, secondary text |
| Danger | `#dc2626` (red-600) | Destructive actions |
| Success | `#16a34a` (green-600) | Positive states |

## Typography

- **Font:** system-ui, -apple-system, sans-serif
- **Headings:** font-semibold, text sizes from `text-sm` to `text-5xl`
- **Body:** text-sm, leading-relaxed
- **Monospace:** (inherited from system)

## Layout

- **Max content width:** 80rem (max-w-7xl)
- **Sidebar:** Not at v1. Future: mobile-first bottom nav → desktop sidebar.
- **Density:** Normal (py-3 for table rows, gap-4 for form fields)
- **Border radius:** 0.5rem (rounded-lg), 1rem (rounded-xl for cards)

## Dark Mode

Supported via Tailwind `dark:` variants. Default: follow system preference. Future: toggle.

## Navigation

- Top nav bar with app name, dashboard link, user badge, env badge, logout
- Dashboard as the authenticated landing page
- No sidebar at v1

## Components

- **Buttons:** rounded-lg, py-2 px-4, text-sm font-medium. Primary = blue-600, Secondary = gray border
- **Cards:** rounded-xl, border, bg-white, p-6, shadow-sm
- **Tables:** divide-y, text-sm, hover:bg-gray-50 rows
- **Forms:** border, rounded-lg, py-2 px-3, text-sm. Labels above inputs.
- **Badges:** inline-flex, rounded-md, px-2 py-0.5, text-xs font-medium

## Icons

No icon library at v1. Use inline SVG or emoji sparingly. Future: Lucide.

## To Customize

Edit `DESIGN_TOKENS.json` and run `make generate-tokens`. This regenerates:
- app/static/generated/tokens.css (HTMX :root variables)
- frontend/src/styles/tokens.generated.css (React @theme variables)
Review and commit both files. The color palette table below should match DESIGN_TOKENS.json values.
