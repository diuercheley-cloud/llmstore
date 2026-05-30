# Navigation System - Admin Frontend

Standardized navigation, layout, and design system for the admin portal.

## Architecture

```
frontend/admin/src/
  navigation/
    navConfig.ts              # Single source of truth for all routes + metadata
  components/layout/
    AdminShell.tsx            # Main layout (sidebar + header + content)
    Sidebar.tsx               # Navigation sidebar with collapsible sections
    Breadcrumbs.tsx           # Auto-generated breadcrumbs from URL
    FeatureGate.tsx           # Feature disabled / coming soon page
    PageHeader.tsx            # Standardized page header with title, badge, actions
  index.css                   # Design tokens (light + dark mode)
  App.tsx                     # Router using navConfig + AdminShell
  pages/Hub.tsx               # Hub dashboard built from navConfig
```

## navConfig.ts

Single source of truth. Every route has:

```typescript
interface NavRoute {
  path: string           // URL path
  label: string          // Display name
  icon: LucideIcon       // Icon component
  section: string        // Sidebar group key
  featureFlag: string    // Feature gate key
  status: 'active' | 'beta' | 'coming_soon' | 'disabled'
  hidden?: boolean       // Hidden from sidebar, still routable
  parentPath?: string    // For breadcrumb nesting
}
```

### Sections

| Key | Label | Feature Flag |
|-----|-------|-------------|
| `core` | Core | agents |
| `agents` | Agentic Platform | agents |
| `operations` | Operations | operations |
| `performance` | Performance | performance |
| `enterprise` | Enterprise | enterprise |
| `observability` | Observability | observability |
| `compliance` | Compliance | compliance |
| `advanced` | Advanced | advanced |
| `developers` | Developers | developers |

### Route Status

| Status | Behavior |
|--------|----------|
| `active` | Normal link |
| `beta` | Shows "Beta" badge |
| `coming_soon` | Shows "Soon" badge, link disabled |
| `disabled` | Fully disabled |

## Layout Components

### AdminShell
Main layout wrapper. All pages render inside it:
```tsx
<AdminShell>
  <MyPage />
</AdminShell>
```

### Sidebar
- Collapsible sections (single item = flat link, multiple = accordion)
- Active state highlighting
- Status badges (Beta, Soon)
- Mobile responsive with backdrop

### Breadcrumbs
- Auto-generated from URL path
- Uses navConfig for label resolution
- Clickable intermediate segments

### FeatureGate
Shown when a feature is disabled or coming soon:
```tsx
<FeatureGate feature="Chaos Engineering" />
```

### PageHeader
Standardized page header:
```tsx
<PageHeader
  title="Agentes"
  subtitle="Gerencie seus agentes IA"
  icon={<Bot />}
  badge="Beta"
  badgeVariant="beta"
  actions={<Button>Novo</Button>}
/>
```

## Design Tokens

### Colors (Light/Dark)
| Token | Light | Dark |
|-------|-------|------|
| `background` | slate-50 | slate-950 |
| `foreground` | slate-900 | slate-50 |
| `card` | white | slate-900 |
| `primary` | teal-600 | teal-500 |
| `secondary` | slate-100 | slate-800 |
| `muted-foreground` | slate-500 | slate-400 |
| `destructive` | red-600 | red-400 |
| `border` | slate-200 | slate-800 |

### Shadows
```css
--shadow-card: 0 1px 3px 0 rgb(0 0 0 / 0.04)
--shadow-card-hover: 0 4px 12px 0 rgb(0 0 0 / 0.08)
--shadow-dropdown: 0 10px 25px -5px rgb(0 0 0 / 0.1)
```

### Utility Classes
- `.card-base` - Standard card with shadow
- `.card-interactive` - Card with hover effect
- `.page-container` - Max-width container

## Hub

Hub cards are built from `navRoutes` + `hubCardMeta`:
- Every nav route with metadata becomes a Hub card
- Status determines card appearance (disabled, badge)
- No dead links - all hrefs come from navConfig

## Adding a New Route

1. Add entry to `navRoutes` in `navConfig.ts`
2. Add lazy import and entry to `componentMap` in `App.tsx`
3. Add metadata to `hubCardMeta` if it should appear on Hub
4. Route appears in sidebar, breadcrumbs, and Hub automatically

## Adding a New Section

1. Add to `navSections` array in `navConfig.ts`
2. Add section icon to `sectionIconMap` in `Sidebar.tsx`
3. Routes with matching `section` key appear in the group
