'use client';

import { useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { CreateScanPayload, Scan, ScanStatus } from '@/types';

// Intervalo de polling para diferentes estados
const POLLING_INTERVALS = {
  running: 2000,    // 2 segundos cuando está corriendo
  pending: 5000,    // 5 segundos cuando está pendiente
  queued: 3000,     // 3 segundos cuando está en cola
  idle: false,      // No polling para estados finales
} as const;

/**
 * Hook para obtener la lista de scans con auto-refresh inteligente
 * Hace polling cada 5 segundos si hay scans activos (running/pending/queued)
 */
export function useScans(params?: { status?: string; type?: string; search?: string }) {
  const query = useQuery({
    queryKey: ['scans', params],
    queryFn: () => api.getScans(params),
    refetchInterval: (query) => {
      const response = query.state.data as { items: Scan[] } | undefined;
      if (!response?.items) return false;
      
      // Si hay algún scan activo, hacer polling cada 5 segundos
      const hasActiveScans = response.items.some(
        (scan) => ['running', 'pending', 'queued'].includes(scan.status)
      );
      return hasActiveScans ? 5000 : false;
    },
  });

  return query;
}

/**
 * Hook para obtener un scan específico con polling inteligente
 * El intervalo de polling depende del estado del scan
 */
export function useScan(id: string) {
  return useQuery({
    queryKey: ['scan', id],
    queryFn: () => api.getScan(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const scan = query.state.data as Scan | undefined;
      if (!scan) return false;
      
      // Determinar intervalo según estado
      if (scan.status === 'running') return POLLING_INTERVALS.running;
      if (scan.status === 'pending') return POLLING_INTERVALS.pending;
      if (scan.status === 'queued') return POLLING_INTERVALS.queued;
      
      // No hacer polling para estados finales
      return POLLING_INTERVALS.idle;
    },
  });
}

/**
 * Hook específico para monitorear el estado de un scan en tiempo real
 * Optimizado para mostrar progreso y actualizaciones frecuentes
 */
export function useScanStatus(scanId: string) {
  const queryClient = useQueryClient();
  
  const query = useQuery({
    queryKey: ['scan-status', scanId],
    queryFn: () => api.getScan(scanId),
    enabled: !!scanId,
    refetchInterval: (query) => {
      const scan = query.state.data as Scan | undefined;
      if (!scan) return 2000;
      
      // Polling más frecuente cuando está corriendo
      if (scan.status === 'running') return 2000;
      if (scan.status === 'pending' || scan.status === 'queued') return 3000;
      
      // Detener polling cuando el scan termina
      return false;
    },
    staleTime: 1000, // Considerar datos stale después de 1 segundo
  });

  // Invalidar la lista de scans cuando el scan se complete
  useEffect(() => {
    if (query.data?.status === 'completed' || query.data?.status === 'failed') {
      queryClient.invalidateQueries({ queryKey: ['scans'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    }
  }, [query.data?.status, queryClient]);

  return query;
}

/**
 * Hook para verificar si hay scans activos
 */
export function useHasActiveScans() {
  const { data: scansResponse } = useScans();
  const scans = scansResponse?.items || [];
  
  return {
    hasActive: scans.some((scan) => 
      ['running', 'pending', 'queued'].includes(scan.status)
    ),
    runningCount: scans.filter((scan) => scan.status === 'running').length,
    pendingCount: scans.filter((scan) => 
      ['pending', 'queued'].includes(scan.status)
    ).length,
  };
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
