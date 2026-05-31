# Mobile PWA Foundation

## Overview

The AI Agent Platform is designed with a mobile-first approach using Progressive Web App (PWA) technology. This allows users to install the portal on their mobile devices, receive push notifications, and access basic features offline without the overhead of a native app store deployment.

## Features

- **Installable**: Full PWA manifest allows "Add to Home Screen" on iOS and Android.
- **Service Worker**: Manages caching of static assets and handles background push events.
- **Push Notifications**: Opt-in system for real-time alerts from agents (requires HTTPS).
- **Responsive Shell**: `MobileShell.tsx` provides a native-like navigation experience with a collapsible sidebar and sticky header.
- **Device Registry**: Automatically registers mobile devices upon login to associate push tokens with tenants.

## PWA Assets

- `public/manifest.webmanifest`: App identity, icons, and theme colors.
- `public/sw.js`: Service worker logic for caching and push.
- `public/offline.html`: Fallback page when network is unavailable and asset is not cached.

## Backend Integration

The mobile foundation relies on the following endpoints:

- `POST /v1/mobile/devices/register`: Records device metadata and tokens.
- `POST /v1/mobile/push/subscribe`: Stores WebPush subscriptions for the current user.
- `POST /v1/mobile/push/unsubscribe`: Removes a subscription.
- `GET /v1/mobile/config`: Returns mobile-specific feature flags and configuration.

## Feature Flags

Mobile features are controlled by these flags in `control_plane/app/core/config.py`:

- `MOBILE_FOUNDATION_ENABLED`: Enables/disables the mobile shell and device registration.
- `PUSH_NOTIFICATIONS_ENABLED`: Enables/disables the push notification opt-in UI and backend services.

## Development

### Testing PWA Local
PWAs typically require HTTPS. For local development, you can use `localhost` (which is treated as secure) or tools like `ngrok` to test on real mobile devices.

### Push Notifications
Push notifications require VAPID keys. Set `VITE_VAPID_PUBLIC_KEY` in your `.env` file for the frontend to enable the subscription flow.
