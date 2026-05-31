# Admin Navigation System

## Overview

The Admin Navigation System is a centralized, configuration-driven architecture for managing the layout, routing, and discovery of features in the Admin Panel. It ensures a consistent user experience (UX) and simplifies the process of adding or restricting access to pages.

## Architecture

- **`navConfig.ts`**: The single source of truth for all navigation metadata. Defines paths, labels, icons, sections, and feature flags.
- **`adminRoutes.tsx`**: Maps the navigation configuration to React components and provides helpers for building sidebar groups and breadcrumbs.
- **`AdminShell.tsx`**: The common layout wrapper that provides the Sidebar, Top Header, and content area.
- **`App.tsx`**: Orchestrates the routing and applies security/feature gating globally.

## Adding a New Page

1.  **Create the Component**: Add your page component to `frontend/admin/src/pages/`.
2.  **Update `navConfig.ts`**: Add a new entry to the `navConfig` array.
    ```typescript
    {
      label: 'My New Page',
      path: '/my-page',
      icon: MyIcon,
      section: 'agents',
      status: 'active',
      description: 'Optional description for the Hub card.',
      featureFlag: 'MY_FEATURE_ENABLED' // Optional
    }
    ```
3.  **Update `adminRoutes.tsx`**: Add a lazy-loaded entry to the `componentMap`.
    ```typescript
    '/my-page': lazy(() => import('../pages/MyPage')),
    ```

## Feature Gating

The system supports granular feature control via the `status` and `featureFlag` fields in `navConfig`.
- **`coming_soon` / `disabled`**: The route is still accessible but renders the `FeatureGate` component instead of the actual page.
- **`featureFlag`**: If a flag is provided, the `RouteRenderer` in `App.tsx` checks the user settings before rendering.

## Standard Layout Components

- **`PageHeader`**: Standardizes titles, subtitles, and top-level actions.
- **`Breadcrumbs`**: Automatically generated from the URL path.
- **`Sidebar`**: Grouped and collapsible navigation.
- **`Hub`**: A dashboard of all available modules as interactive cards.
