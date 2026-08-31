import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import {
  getStoredToken,
  readError,
  setStoredToken,
  setUnauthorizedHandler,
} from '../services/api.js';
import authService from '../services/authService.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => getStoredToken());
  // "initializing" covers the first /auth/me round trip so protected routes do
  // not redirect a logged-in user to the login page on a hard refresh.
  const [initializing, setInitializing] = useState(true);

  const clearSession = useCallback(() => {
    setStoredToken(null);
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(clearSession);
    return () => setUnauthorizedHandler(null);
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;
    if (!token) {
      setInitializing(false);
      return undefined;
    }
    authService
      .me()
      .then((profile) => {
        if (!cancelled) setUser(profile);
      })
      .catch(() => {
        if (!cancelled) clearSession();
      })
      .finally(() => {
        if (!cancelled) setInitializing(false);
      });
    return () => {
      cancelled = true;
    };
    // Only re-runs when the token itself changes.
  }, [token, clearSession]);

  const login = useCallback(async (email, password) => {
    try {
      const data = await authService.login(email, password);
      setStoredToken(data.access_token);
      setToken(data.access_token);
      setUser(data.user);
      return { ok: true, user: data.user };
    } catch (error) {
      return { ok: false, error: readError(error, 'Unable to sign in.') };
    }
  }, []);

  const register = useCallback(
    async (name, email, password) => {
      try {
        await authService.register({ name, email, password });
        return login(email, password);
      } catch (error) {
        return { ok: false, error: readError(error, 'Unable to create the account.') };
      }
    },
    [login],
  );

  const logout = useCallback(async () => {
    try {
      await authService.logout();
    } catch {
      // The token may already be expired; clearing locally is still correct.
    }
    clearSession();
  }, [clearSession]);

  const value = useMemo(
    () => ({
      user,
      token,
      initializing,
      isAuthenticated: Boolean(user),
      isAdmin: user?.role === 'admin',
      login,
      register,
      logout,
    }),
    [user, token, initializing, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside an AuthProvider');
  return context;
}

export default AuthContext;
