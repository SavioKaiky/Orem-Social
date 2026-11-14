import { useQueryClient } from '@tanstack/react-query';
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

import { api, setSessionExpiredHandler } from './api';
import { digits } from './format';
import { clearTokens, loadTokens, saveTokens } from './tokens';
import { User } from './types';

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Se o refresh falhar em qualquer tela, volta para o login
    setSessionExpiredHandler(() => {
      setUser(null);
      queryClient.clear();
    });

    (async () => {
      try {
        const tokens = await loadTokens();
        if (tokens) setUser(await api<User>('/auth/me/'));
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    })();

    return () => setSessionExpiredHandler(null);
  }, [queryClient]);

  const login = useCallback(async (identifier: string, password: string) => {
    const data = await api<{ access: string; refresh: string; user: User }>('/auth/login/', {
      method: 'POST',
      body: { identifier: digits(identifier), password },
      auth: false,
    });
    await saveTokens({ access: data.access, refresh: data.refresh });
    setUser(data.user);
  }, []);

  const logout = useCallback(async () => {
    await clearTokens();
    queryClient.clear();
    setUser(null);
  }, [queryClient]);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth precisa estar dentro do AuthProvider');
  return context;
}
