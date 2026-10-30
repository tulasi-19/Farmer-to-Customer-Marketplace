import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { authAPI } from '../api/services';
import { tokens } from '../api/axiosClient';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // The role always comes from the SERVER (/auth/me/), not from decoding the token in the browser.
  const loadUser = useCallback(async () => {
    if (!tokens.access()) { setUser(null); setLoading(false); return; }
    try { setUser(await authAPI.me()); } catch { tokens.clear(); setUser(null); }
    setLoading(false);
  }, []);

  useEffect(() => { loadUser(); }, [loadUser]);
  useEffect(() => {
    const onLogout = () => setUser(null);
    window.addEventListener('auth:logout', onLogout);
    return () => window.removeEventListener('auth:logout', onLogout);
  }, []);

  const login = async (username, password) => {
    const res = await authAPI.login({ username, password });
    tokens.set(res);
    const me = await authAPI.me();
    setUser(me);
    return me;
  };

  const logout = async () => {
    const refresh = tokens.refresh();
    try { if (refresh) await authAPI.logout(refresh); } catch { /* token already invalid: fine */ }
    tokens.clear();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, reloadUser: loadUser, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}
