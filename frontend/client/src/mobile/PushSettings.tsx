import { useState, useEffect, useCallback } from 'react';
import { Bell, BellOff, Smartphone, Loader2, Wifi, WifiOff } from 'lucide-react';
import {
  registerServiceWorker,
  subscribePushNotifications,
  unsubscribePushNotifications,
  getPushSubscription,
  isPushSupported,
  getNotificationPermission,
} from '../lib/pwa';

export function PushSettings() {
  const [swReg, setSwReg] = useState<ServiceWorkerRegistration | null>(null);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [permission, setPermission] = useState<NotificationPermission>('default');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [supported] = useState(isPushSupported());
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  const loadState = useCallback(async () => {
    setLoading(true);
    try {
      const reg = await registerServiceWorker();
      setSwReg(reg);
      if (reg) {
        const sub = await getPushSubscription(reg);
        setIsSubscribed(!!sub);
      }
      setPermission(getNotificationPermission());
    } catch {
      // SW not available
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadState();
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [loadState]);

  const handleEnable = async () => {
    if (!swReg) return;
    setActionLoading(true);
    const sub = await subscribePushNotifications(swReg);
    if (sub) {
      setIsSubscribed(true);
      setPermission('granted');
    }
    setActionLoading(false);
  };

  const handleDisable = async () => {
    if (!swReg) return;
    setActionLoading(true);
    const ok = await unsubscribePushNotifications(swReg);
    if (ok) {
      setIsSubscribed(false);
    }
    setActionLoading(false);
  };

  return (
    <div className="space-y-6">
      {/* Offline banner */}
      {isOffline && (
        <div className="flex items-center gap-2 p-3 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-700">
          <WifiOff size={16} />
          <span>You are offline. Some features may be limited.</span>
        </div>
      )}

      {/* Push notifications */}
      <div className="card space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Bell size={20} className="text-primary" />
          </div>
          <div>
            <h3 className="font-semibold text-text-base">Push Notifications</h3>
            <p className="text-sm text-slate-500">
              {loading ? 'Loading...' : isSubscribed ? 'Enabled' : 'Disabled'}
            </p>
          </div>
        </div>

        {!supported ? (
          <p className="text-sm text-slate-400">
            Push notifications are not available on this device.
          </p>
        ) : (
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-500">
              Status: {permission === 'granted' ? 'Allowed' : permission === 'denied' ? 'Blocked' : 'Not set'}
            </span>
            {loading ? (
              <Loader2 size={18} className="animate-spin text-slate-400" />
            ) : (
              <button
                onClick={isSubscribed ? handleDisable : handleEnable}
                disabled={actionLoading || permission === 'denied'}
                className={`btn ${isSubscribed ? 'btn-outline' : 'btn-primary'} text-sm`}
              >
                {actionLoading ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : isSubscribed ? (
                  <><BellOff size={14} /> Disable</>
                ) : (
                  <><Bell size={14} /> Enable</>
                )}
              </button>
            )}
          </div>
        )}

        {permission === 'denied' && (
          <p className="text-xs text-red-500">
            Notifications are blocked by your browser. Enable them in browser settings.
          </p>
        )}
      </div>

      {/* Offline support info */}
      <div className="card space-y-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-slate-100 rounded-lg">
            <Smartphone size={20} className="text-slate-600" />
          </div>
          <div>
            <h3 className="font-semibold text-text-base">Offline Support</h3>
            <p className="text-sm text-slate-500">Service worker manages caching</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-sm">
          {navigator.onLine ? (
            <>
              <Wifi size={16} className="text-green-500" />
              <span className="text-slate-600">Online - Static assets cached for offline</span>
            </>
          ) : (
            <>
              <WifiOff size={16} className="text-amber-500" />
              <span className="text-slate-600">Offline - Serving cached content</span>
            </>
          )}
        </div>
        <p className="text-xs text-slate-400">
          API data requires an internet connection. Static assets (HTML, CSS, JS) are cached locally.
          Sensitive data is never cached by default.
        </p>
      </div>
    </div>
  );
}
