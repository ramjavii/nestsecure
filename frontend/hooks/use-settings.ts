'use client';

/**
 * useSettings Hook
 * 
 * Manages user profile and settings with API integration.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useAuthStore } from '@/lib/stores/auth-store';
import { useToast } from '@/hooks/use-toast';
import type { User } from '@/types';

interface ProfileUpdatePayload {
  full_name?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
}

interface PasswordChangePayload {
  current_password: string;
  new_password: string;
}

/**
 * Hook for managing current user profile
 */
export function useCurrentUser() {
  const storeUser = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);

  const query = useQuery({
    queryKey: ['currentUser'],
    queryFn: async () => {
      const user = await api.getCurrentUser();
      // Update store with fresh data
      setUser(user);
      return user;
    },
    initialData: storeUser || undefined,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });

  return {
    user: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

/**
 * Hook for updating user profile
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);

  const mutation = useMutation({
    mutationFn: async (payload: ProfileUpdatePayload) => {
      if (!user?.id) throw new Error('No user logged in');
      return api.updateUser(user.id, payload);
    },
    onSuccess: (updatedUser) => {
      // Update the auth store
      setUser(updatedUser);
      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      toast({
        title: 'Perfil actualizado',
        description: 'Los cambios han sido guardados correctamente.',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error al actualizar perfil',
        description: error.message || 'No se pudieron guardar los cambios.',
        variant: 'destructive',
      });
    },
  });

  return {
    updateProfile: mutation.mutate,
    updateProfileAsync: mutation.mutateAsync,
    isUpdating: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Hook for changing password
 */
export function useChangePassword() {
  const { toast } = useToast();
  const user = useAuthStore((state) => state.user);

  const mutation = useMutation({
    mutationFn: async (payload: PasswordChangePayload) => {
      if (!user?.id) throw new Error('No user logged in');
      return api.changePassword(user.id, payload);
    },
    onSuccess: () => {
      toast({
        title: 'Contraseña actualizada',
        description: 'Tu contraseña ha sido cambiada correctamente.',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Error al cambiar contraseña',
        description: error.message || 'No se pudo cambiar la contraseña.',
        variant: 'destructive',
      });
    },
  });

  return {
    changePassword: mutation.mutate,
    changePasswordAsync: mutation.mutateAsync,
    isChanging: mutation.isPending,
    error: mutation.error,
  };
}

/**
 * Composite hook for all settings functionality
 */
export function useSettings() {
  const { user, isLoading, refetch } = useCurrentUser();
  const { updateProfile, updateProfileAsync, isUpdating } = useUpdateProfile();
  const { changePassword, changePasswordAsync, isChanging } = useChangePassword();

  return {
    // User data
    user,
    isLoading,
    refetchUser: refetch,
    
    // Profile updates
    updateProfile,
    updateProfileAsync,
    isUpdating,
    
    // Password changes
    changePassword,
    changePasswordAsync,
    isChanging,
    
    // Combined loading state
    isSaving: isUpdating || isChanging,
  };
}
