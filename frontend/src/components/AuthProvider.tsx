'use client';

import { useState, useEffect, useCallback, ReactNode } from 'react';
import { AuthContext, getStoredTokens, setStoredTokens, clearStoredTokens } from '@/lib/auth';
import { authApi } from '@/lib/api';
import type { User, AuthTokens } from '@/types';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for stored tokens on mount
  useEffect(() => {
    const stored = getStoredTokens();
    if (stored) {
      setTokens(stored);
      // Fetch user info
      authApi.me(stored.access_token)
        .then((userData) => {
          setUser(userData as User);
        })
        .catch(() => {
          clearStoredTokens();
          setTokens(null);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const tokenData = await authApi.login(username, password) as AuthTokens;
    setStoredTokens(tokenData);
    setTokens(tokenData);

    const userData = await authApi.me(tokenData.access_token) as User;
    setUser(userData);
  }, []);

  const logout = useCallback(() => {
    clearStoredTokens();
    setTokens(null);
    setUser(null);
  }, []);

  const register = useCallback(async (data: {
    username: string;
    email: string;
    password: string;
    full_name?: string;
  }) => {
    await authApi.register(data);
    // Auto-login after registration
    await login(data.username, data.password);
  }, [login]);

  return (
    <AuthContext.Provider value={{ user, tokens, isLoading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
}
