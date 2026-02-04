'use client';

import { useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { api } from '@/lib/api';
import type { LoginCredentials } from '@/types';

export function useAuth() {
  const router = useRouter();
  const { 
    user, 
    accessToken, 
    isAuthenticated, 
    isLoading,
    setUser, 
    setTokens, 
    logout: storeLogout,
    setLoading,
  } = useAuthStore();

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      if (accessToken && !user) {
        try {
          const userData = await api.getMe();
          setUser(userData);
        } catch {
          storeLogout();
        }
      }
      setLoading(false);
    };

    initAuth();
  }, [accessToken, user, setUser, storeLogout, setLoading]);

  const login = useCallback(async (credentials: LoginCredentials) => {
    const response = await api.login(credentials);
    setTokens(response.access_token, response.refresh_token);
    
    const userData = await api.getMe();
    setUser(userData);
    
    router.push('/');
  }, [setTokens, setUser, router]);

  const logout = useCallback(() => {
    storeLogout();
    router.push('/login');
  }, [storeLogout, router]);

  return {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
  };
}
