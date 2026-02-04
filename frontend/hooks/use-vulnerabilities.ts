'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { UpdateVulnerabilityPayload } from '@/types';

export function useVulnerabilities(params?: {
  severity?: string;
  status?: string;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}) {
  return useQuery({
    queryKey: ['vulnerabilities', params],
    queryFn: () => api.getVulnerabilities(params),
  });
}

export function useVulnerability(id: string) {
  return useQuery({
    queryKey: ['vulnerability', id],
    queryFn: () => api.getVulnerability(id),
    enabled: !!id,
  });
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
