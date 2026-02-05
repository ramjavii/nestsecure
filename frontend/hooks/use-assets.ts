'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { CreateAssetPayload } from '@/types';

export function useAssets(params?: { 
  type?: string; 
  criticality?: string; 
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: ['assets', params],
    queryFn: () => api.getAssets({ page_size: 500, ...params }),
  });
}

export function useAsset(id: string) {
  return useQuery({
    queryKey: ['asset', id],
    queryFn: () => api.getAsset(id),
    enabled: !!id,
  });
}

export function useAssetServices(id: string) {
  return useQuery({
    queryKey: ['asset', id, 'services'],
    queryFn: () => api.getAssetServices(id),
    enabled: !!id,
  });
}

export function useAssetVulnerabilities(id: string) {
  return useQuery({
    queryKey: ['asset', id, 'vulnerabilities'],
    queryFn: () => api.getAssetVulnerabilities(id),
    enabled: !!id,
  });
}

export function useAssetScans(id: string) {
  return useQuery({
    queryKey: ['asset', id, 'scans'],
    queryFn: () => api.getAssetScans(id),
    enabled: !!id,
  });
}

export function useCreateAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateAssetPayload) => api.createAsset(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useUpdateAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<CreateAssetPayload> }) => 
      api.updateAsset(id, payload),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['asset', id] });
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}

export function useDeleteAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteAsset(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets'] });
    },
  });
}
