'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { CreateScanPayload } from '@/types';

export function useScans(params?: { status?: string; type?: string; search?: string }) {
  return useQuery({
    queryKey: ['scans', params],
    queryFn: () => api.getScans(params),
  });
}

export function useScan(id: string) {
  return useQuery({
    queryKey: ['scan', id],
    queryFn: () => api.getScan(id),
    enabled: !!id,
  });
}

export function useCreateScan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateScanPayload) => api.createScan(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useStopScan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.stopScan(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['scan', id] });
      queryClient.invalidateQueries({ queryKey: ['scans'] });
    },
  });
}

export function useDeleteScan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteScan(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scans'] });
    },
  });
}
