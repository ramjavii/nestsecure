'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { UpdateVulnerabilityPayload, Vulnerability } from '@/types';

export function useVulnerabilities(params?: {
  severity?: string;
  status?: string;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}) {
  const query = useQuery({
    queryKey: ['vulnerabilities', params],
    queryFn: () => api.getVulnerabilities(params),
  });

  return {
    vulnerabilities: query.data || [] as Vulnerability[],
    isLoading: query.isLoading,
    error: query.error,
    pagination: {
      total: query.data?.length || 0,
      page: params?.page || 1,
      pages: 1,
    },
    refetch: query.refetch,
  };
}

export function useVulnerability(id: string) {
  const query = useQuery({
    queryKey: ['vulnerability', id],
    queryFn: () => api.getVulnerability(id),
    enabled: !!id,
  });

  return {
    vulnerability: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

export function useUpdateVulnerability() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UpdateVulnerabilityPayload }) =>
      api.updateVulnerability(id, payload),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['vulnerability', id] });
      queryClient.invalidateQueries({ queryKey: ['vulnerabilities'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
}

export function useUpdateVulnerabilityStatus() {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.updateVulnerability(id, { status } as UpdateVulnerabilityPayload),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['vulnerability', id] });
      queryClient.invalidateQueries({ queryKey: ['vulnerabilities'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  return {
    updateStatus: (id: string, status: string) => mutation.mutateAsync({ id, status }),
    isUpdating: mutation.isPending,
  };
}
