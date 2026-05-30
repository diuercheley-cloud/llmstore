# PWA & Mobile Foundation

Progressive Web App base for the client portal. Installable, mobile-friendly, with offline support and push notifications.

## Architecture

```
frontend/client/
  public/
    manifest.webmanifest      # PWA manifest
    sw.js                     # Service worker (caching + push)
    offline.html              # Offline fallback page
    icons/                    # App icons (192, 512)
  src/
    lib/pwa.ts                # SW registration, push subscribe/unsubscribe
    mobile/
      MobileShell.tsx         # Responsive layout shell (sidebar + content)
      PushSettings.tsx         # Push notification opt-in/out UI
    main.tsx                  # Registers service worker on load

control_plane/
  app/models/mobile.py        # MobileDevice, MobileSession, PushSubscription, PushNotificationEvent
  app/api/mobile_v1.py        # REST endpoints for devices, sessions, push
  app/services/mobile/
    device_registry.py        # Device register/deactivate
    mobile_session.py         # Session create/validate
    push_notifications.py     # Send push (mock FCM/APNs)
```

## Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `MOBILE_FOUNDATION_ENABLED` | `false` | Gates all `/v1/mobile/*` endpoints |
| `PUSH_NOTIFICATIONS_ENABLED` | `false` | Gates push send functionality |

Set in environment:
```bash
MOBILE_FOUNDATION_ENABLED=true
PUSH_NOTIFICATIONS_ENABLED=true
```

## API Endpoints

All endpoints require `Authorization: Bearer <token>` and are gated by `MOBILE_FOUNDATION_ENABLED`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/mobile/devices` | Register/update device |
| GET | `/v1/mobile/devices` | List tenant devices |
| DELETE | `/v1/mobile/devices/{token}` | Deactivate device |
| POST | `/v1/mobile/sessions` | Start mobile session |
| POST | `/v1/mobile/push/subscribe` | Register web push subscription (VAPID) |
| DELETE | `/v1/mobile/push/subscribe` | Remove push subscription |
| GET | `/v1/mobile/push/status` | Check push config status |
| GET | `/v1/mobile/feed` | Recent activity feed |
| POST | `/v1/mobile/push/test` | Send test push |

## PWA Configuration

### Manifest
- `display: standalone` - no browser chrome
- `orientation: portrait-primary`
- `theme_color: #3b82f6` (matches CSS primary)
- Icons at 192x192 and 512x512

### Service Worker
- **Static assets**: Cache-first with network fallback
- **API requests**: Network only (no cache) - returns 503 offline JSON
- **No sensitive data cached** by default
- Push event handler shows notifications
- Notification click focuses/opens app

### VAPID Keys
For web push, generate VAPID keys and set:
```bash
VITE_VAPID_PUBLIC_KEY=<your-public-key>
```

## Mobile Layout

`MobileShell` provides:
- Collapsible sidebar (hamburger on mobile, static on desktop)
- Touch-friendly navigation
- `100dvh` height for mobile browsers
- Responsive breakpoints at `lg` (1024px)

## Security

- Device tokens are tenant-scoped (validated on all endpoints)
- Push subscriptions are per-tenant
- No API data cached in service worker
- Session tokens expire after 30 days
- Bearer auth required for all endpoints

## Testing

- Manifest exists at `/manifest.webmanifest`
- Service worker registers on page load
- Mobile layout renders on small viewports
- Push disabled by default (requires feature flags)
- Device registration validates tenant isolation
