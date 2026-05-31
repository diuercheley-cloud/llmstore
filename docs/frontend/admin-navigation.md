# Admin Navigation System

## Overview

The Admin Navigation System provides a centralized way to manage routes, sidebar grouping, and breadcrumbs in the Admin Panel. It uses a "Route-First" approach where all metadata is defined in a single configuration file.

## Central Route Map (`adminRoutes.tsx`)

The single source of truth for all admin routes is located at `frontend/admin/src/routes/adminRoutes.tsx`.

Each route entry contains:
- `path`: The URL path.
- `component`: The lazy-loaded page component.
- `label`: Display name used in sidebar and breadcrumbs.
- `icon`: Lucide icon component.
- `group`: Sidebar section key (e.g., `core`, `agents`, `operations`).
- `status`: `active`, `beta`, `coming_soon`, or `disabled`.
- `hidden`: If `true`, the route is accessible but not visible in the sidebar.
- `description`: Text shown on the Hub cards.

## Sidebar Organization

The sidebar is built automatically using the `buildSidebarGroups` helper. Groups are ordered as follows:
1. Core
2. Agentic Platform
3. Operations
4. Performance
5. Enterprise
6. Observability
7. Compliance
8. Advanced
9. Developers

Sections with multiple routes become collapsible groups, while single-route sections appear as flat links.

## Hub Page

The Admin Hub (`/`) dynamically renders cards for all visible routes. It uses the `status` field to:
- Show a "Soon" badge for `coming_soon` routes.
- Apply a "Beta" look for `beta` routes.
- Disable interactions for `disabled` or `coming_soon` status.

## Adding a New Page

1. Create your component in `frontend/admin/src/pages/`.
2. Open `frontend/admin/src/routes/adminRoutes.tsx`.
3. Add a lazy import for your component.
4. Add a new entry to the `routes` array.
5. The page will automatically appear in:
   - The React Router switch in `App.tsx`.
   - The Sidebar (unless `hidden` is true).
   - The Admin Hub.
   - The Breadcrumbs trail.
   - The Command Palette (Ctrl+K).
