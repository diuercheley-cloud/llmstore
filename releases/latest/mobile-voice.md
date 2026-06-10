# PWA/Mobile + Voice/WebRTC Foundation

## Status: IMPLEMENTED

## PWA/Mobile Foundation

### Components
- **Service Worker**: `frontend/client/public/sw.js` - Offline support and caching
- **Web Manifest**: `frontend/client/public/manifest.webmanifest` - PWA manifest
- **Offline Page**: `frontend/client/public/offline.html` - Graceful offline fallback
- **Mobile Components**: `frontend/client/src/mobile/` - Mobile-specific UI

### Capabilities
- Installable PWA on mobile devices
- Offline caching strategy
- Mobile-responsive chat interface
- Touch-optimized interactions

## Voice/WebRTC Foundation

### Backend Components
- **API**: `control_plane/app/api/voice.py` - Voice agent REST endpoints
- **Services**: `control_plane/app/services/voice/` - Voice processing services
- **Config**: `control_plane/app/core/config.py` - Voice feature flags

### Feature Flags
| Flag | Default | Description |
|------|---------|-------------|
| `VOICE_AGENT_ENABLED` | false | Voice agent support |
| `VOICE_STT_STREAMING_ENABLED` | false | Speech-to-text streaming |
| `VOICE_TTS_STREAMING_ENABLED` | false | Text-to-speech streaming |
| `WEBRTC_VOICE_ENABLED` | false | WebRTC voice calls |
| `WEBRTC_AUDIO_ENABLED` | false | WebRTC audio foundation |

### Documentation
- `docs/voice/` - Voice agent architecture and configuration
- `docs/mobile/pwa.md` - PWA setup and deployment
