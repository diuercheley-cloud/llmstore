# Admin Navigation - Route & Hub Integration

## Architecture Changes

### Centralized Route Registry

**File:** `frontend/admin/src/routes/adminRoutes.tsx`

All routes are now defined in a single source of truth. Each route entry contains:
- `path` - URL path
- `component` - Lazy-loaded React component
- `label` - Display name
- `icon` - Lucide icon
- `group` - Sidebar group key
- `disabled` - Shows "Coming Soon" badge
- `hidden` - Hidden from sidebar but still routable

### Route Groups

| Group | Label | Routes |
|-------|-------|--------|
| `core` | Core | Hub, Clients, Models, Backends, Plugins, SaaS |
| `agents` | Agentic Platform | Overview, Registry, Runs, Tools, Memory, Approvals, Evals, Policies, Marketplace, Workspaces, **Studio**, **Analytics**, **Approval Portal**, **Promotion**, **Lineage**, **Chat** |
| `operations` | Operations | Overview, Nodes, Runtime, QoS, Readiness, Security, Release, Incidents |
| `performance` | Performance | Dashboard, History, Profiles |
| `enterprise` | Enterprise | Onboarding, Checklist |
| `observability` | Observability | Dashboard, Realtime, Agent Observability |
| `compliance` | Compliance | Overview, Controls, Evidence, Risks, Policies |
| `advanced` | Advanced | Multi-Cluster (disabled), Chaos (disabled) |
| `developers` | Developers | **Web IDE**, **Developer Portal** |

### Previously Orphan Pages (Now Connected)

| Page | Route | Status |
|------|-------|--------|
| Agent Studio | `/agents/studio` | Connected |
| Agent Analytics | `/agents/analytics` | Connected |
| Approval Portal | `/agents/approvals-portal` | Connected |
| Collaborative Chat | `/agents/chat` | Connected |
| Web IDE | `/ide` | Connected |
| Developer Portal | `/developers` | Connected |
| Agent Promotion | `/agents/promotion` | Connected (rewritten to Tailwind) |
| Agent Lineage | `/agents/lineage` | Connected (rewritten to Tailwind) |

### Placeholder Routes (Coming Soon)

| Route | Page |
|-------|------|
| `/api-keys` | Coming Soon |
| `/billing` | Coming Soon |
| `/usage` | Coming Soon |
| `/rag` | Coming Soon |
| `/security` | Coming Soon |
| `/reports` | Coming Soon |
| `/settings` | Coming Soon |

These show a "Coming Soon" stub with a construction icon and badge.

## Component Changes

### New Files

| File | Purpose |
|------|---------|
| `src/routes/adminRoutes.tsx` | Centralized route registry, sidebar group builder |
| `src/components/Layout.tsx` | Extracted Layout with sidebar, header, breadcrumbs |
| `src/components/ComingSoon.tsx` | Placeholder component for unbuilt pages |

### Modified Files

| File | Change |
|------|--------|
| `src/App.tsx` | Rewritten to use `adminRoutes` + `Layout`, generates routes dynamically |
| `src/pages/Hub.tsx` | Rewritten: dead links fixed, cards built from route registry, "Soon" badges |
| `src/components/command-palette.tsx` | Added 7 new shortcuts (Studio, Analytics, Approvals, Chat, IDE, Developers, Agents) |
| `src/pages/agents/AgentPromotion.tsx` | Rewritten from MUI to Tailwind (MUI not in deps) |
| `src/pages/agents/AgentLineage.tsx` | Rewritten from MUI to Tailwind (MUI not in deps) |

### Sidebar Structure

The sidebar now uses collapsible groups:

```
Hub
─── Agentic Platform (expanded by default)
    ├── Agentes
    ├── Agent Studio
    ├── Analytics
    ├── Approval Portal
    ├── Promotion
    ├── Lineage
    └── Chat Colaborativo
─── Operations
    └── Operacoes
─── Performance
    └── Performance
─── Enterprise
    └── Enterprise Onboarding
─── Observability
    └── Observabilidade
─── Compliance
    └── Compliance
─── Advanced
    ├── Multi-Cluster (Soon)
    └── Chaos Engineering (Soon)
─── Developers
    ├── Web IDE
    └── Developer Portal
Sair
```

### Breadcrumbs

Breadcrumb navigation is automatically generated from the URL path:
- `/agents/studio` -> Hub > Agents > Studio
- `/compliance/controls` -> Hub > Compliance > Controls

### Hub Cards

Hub cards are now built from the route registry. Every card links to a real route.
- Active routes show "Ver Mais" with arrow
- Disabled/placeholder routes show "Em Breve" with construction icon and "Soon" badge

## Adding a New Route

1. Add the route entry to `src/routes/adminRoutes.tsx` in the `routes` array
2. Create the page component in `src/pages/`
3. It will automatically appear in:
   - The sidebar (if not `hidden`)
   - The Hub cards
   - The command palette (add shortcut manually)

## Testing

- All routes render without errors
- Hub has no dead links
- Disabled features show "Coming Soon" badge
- Sidebar navigates correctly with group expand/collapse
- Breadcrumbs update on navigation
- Command palette includes all new pages
