(function(global) {
  "use strict";

  const DEFAULT_KEYS = [
    "adminToken",
    "provider-settings-admin-token",
    "portalApiKey",
    "apiKey",
    "clientToken",
    "token"
  ];

  function safeGet(storage, key) {
    try {
      return storage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function safeSet(storage, key, value) {
    try {
      storage.setItem(key, value);
      return true;
    } catch (error) {
      return false;
    }
  }

  function safeRemove(storage, key) {
    try {
      storage.removeItem(key);
      return true;
    } catch (error) {
      return false;
    }
  }

  function getToken(key, options) {
    const settings = options || {};
    const preferredStorage = settings.storage === "session" ? global.sessionStorage : global.localStorage;
    const fallbackStorage = settings.storage === "session" ? global.localStorage : global.sessionStorage;

    return (
      safeGet(preferredStorage, key) ||
      safeGet(fallbackStorage, key) ||
      null
    );
  }

  function setToken(key, value, options) {
    const settings = options || {};
    const storage = settings.storage === "session" ? global.sessionStorage : global.localStorage;
    return safeSet(storage, key, value);
  }

  function clearToken(key) {
    safeRemove(global.localStorage, key);
    safeRemove(global.sessionStorage, key);
  }

  function readKnownTokens(keys) {
    const list = Array.isArray(keys) && keys.length ? keys : DEFAULT_KEYS;
    const found = {};
    list.forEach(function(key) {
      const value = getToken(key);
      if (value) found[key] = value;
    });
    return found;
  }

  function headerForAdminToken(token) {
    return token ? { "X-Admin-Token": token } : {};
  }

  function headerForBearerToken(token) {
    return token ? { Authorization: "Bearer " + token } : {};
  }

  global.SharedAuth = {
    DEFAULT_KEYS: DEFAULT_KEYS.slice(),
    getToken: getToken,
    setToken: setToken,
    clearToken: clearToken,
    readKnownTokens: readKnownTokens,
    headerForAdminToken: headerForAdminToken,
    headerForBearerToken: headerForBearerToken
  };
})(window);
