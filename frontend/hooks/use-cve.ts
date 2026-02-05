'use client';

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type {
  CVE,
  CVEMinimal,
  CVESearchParams,
  CVEStats,
  CVESyncRequest,
  CVESyncStatus,
  CVELookupResponse,
  PaginatedResponse,
} from '@/types';

// =============================================================================
// Query Keys
// =============================================================================

export const cveKeys = {
  all: ['cve'] as const,
  lists: () => [...cveKeys.all, 'list'] as const,
  list: (params: CVESearchParams) => [...cveKeys.lists(), params] as const,
  details: () => [...cveKeys.all, 'detail'] as const,
  detail: (id: string) => [...cveKeys.details(), id] as const,
  stats: () => [...cveKeys.all, 'stats'] as const,
  syncStatus: () => [...cveKeys.all, 'sync-status'] as const,
  trending: () => [...cveKeys.all, 'trending'] as const,
  kev: () => [...cveKeys.all, 'kev'] as const,
  exploitable: () => [...cveKeys.all, 'exploitable'] as const,
  lookup: (ids: string[]) => [...cveKeys.all, 'lookup', ids] as const,
};

// =============================================================================
// Search CVEs Hook
// =============================================================================

export function useCVESearch(params: CVESearchParams = {}) {
  const query = useQuery({
    queryKey: cveKeys.list(params),
    queryFn: () => api.searchCVEs(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  return {
    cves: query.data?.items || [],
    total: query.data?.total || 0,
    page: query.data?.page || 1,
    pages: query.data?.pages || 1,
    pageSize: query.data?.page_size || 20,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    error: query.error,
    refetch: query.refetch,
  };
}

// =============================================================================
// Infinite Search CVEs Hook (for lazy loading)
// =============================================================================

export function useCVESearchInfinite(params: Omit<CVESearchParams, 'page'> = {}) {
  const query = useInfiniteQuery({
    queryKey: [...cveKeys.list(params), 'infinite'],
    queryFn: ({ pageParam = 1 }) => api.searchCVEs({ ...params, page: pageParam }),
    getNextPageParam: (lastPage) => {
      if (lastPage.page < lastPage.pages) {
        return lastPage.page + 1;
      }
      return undefined;
    },
    initialPageParam: 1,
    staleTime: 5 * 60 * 1000,
  });

  const cves = query.data?.pages.flatMap(page => page.items) || [];

  return {
    cves,
    total: query.data?.pages[0]?.total || 0,
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isFetchingNextPage: query.isFetchingNextPage,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
    error: query.error,
    refetch: query.refetch,
  };
}

// =============================================================================
// Get Single CVE Hook
// =============================================================================

export function useCVE(cveId: string | null | undefined) {
  const query = useQuery({
    queryKey: cveKeys.detail(cveId || ''),
    queryFn: () => api.getCVE(cveId!),
    enabled: !!cveId && cveId.length > 0,
    staleTime: 10 * 60 * 1000, // 10 minutes (CVE data doesn't change often)
  });

  return {
    cve: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

// =============================================================================
// CVE Stats Hook
// =============================================================================

export function useCVEStats() {
  const query = useQuery({
    queryKey: cveKeys.stats(),
    queryFn: () => api.getCVEStats(),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 60 * 1000, // Refresh every minute
  });

  return {
    stats: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

// =============================================================================
// CVE Sync Status Hook
// =============================================================================

export function useCVESyncStatus() {
  const query = useQuery({
    queryKey: cveKeys.syncStatus(),
    queryFn: () => api.getCVESyncStatus(),
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: (query) => {
      // Poll more frequently when sync is running
      if (query.state.data?.status === 'running') {
        return 5 * 1000; // 5 seconds
      }
      return 30 * 1000; // 30 seconds
    },
  });

  return {
    syncStatus: query.data,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
    isRunning: query.data?.status === 'running',
  };
}

// =============================================================================
// Sync CVEs Mutation Hook
// =============================================================================

export function useSyncCVEs() {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (params?: CVESyncRequest) => api.syncCVEs(params),
    onSuccess: () => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: cveKeys.syncStatus() });
      queryClient.invalidateQueries({ queryKey: cveKeys.stats() });
    },
  });

  return {
    sync: mutation.mutate,
    syncAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
    error: mutation.error,
    data: mutation.data,
  };
}

// =============================================================================
// CVE Lookup Hook (for multiple CVEs at once)
// =============================================================================

export function useCVELookup(cveIds: string[]) {
  const query = useQuery({
    queryKey: cveKeys.lookup(cveIds),
    queryFn: () => api.lookupCVEs(cveIds),
    enabled: cveIds.length > 0,
    staleTime: 10 * 60 * 1000,
  });

  return {
    found: query.data?.found || [],
    notFound: query.data?.not_found || [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

// =============================================================================
// Trending CVEs Hook
// =============================================================================

export function useTrendingCVEs(limit: number = 10) {
  const query = useQuery({
    queryKey: [...cveKeys.trending(), limit],
    queryFn: () => api.getTrendingCVEs(limit),
    staleTime: 5 * 60 * 1000,
  });

  return {
    cves: query.data || [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

// =============================================================================
// CISA KEV CVEs Hook
// =============================================================================

export function useKEVCVEs(params?: { page?: number; page_size?: number }) {
  const query = useQuery({
    queryKey: [...cveKeys.kev(), params],
    queryFn: () => api.getKEVCVEs(params),
    staleTime: 5 * 60 * 1000,
  });

  return {
    cves: query.data?.items || [],
    total: query.data?.total || 0,
    page: query.data?.page || 1,
    pages: query.data?.pages || 1,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

// =============================================================================
// Exploitable CVEs Hook
// =============================================================================

export function useExploitableCVEs(params?: { page?: number; page_size?: number }) {
  const query = useQuery({
    queryKey: [...cveKeys.exploitable(), params],
    queryFn: () => api.getExploitableCVEs(params),
    staleTime: 5 * 60 * 1000,
  });

  return {
    cves: query.data?.items || [],
    total: query.data?.total || 0,
    page: query.data?.page || 1,
    pages: query.data?.pages || 1,
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  };
}

// =============================================================================
// Prefetch Helpers
// =============================================================================

export function usePrefetchCVE() {
  const queryClient = useQueryClient();

  return {
    prefetch: (cveId: string) => {
      queryClient.prefetchQuery({
        queryKey: cveKeys.detail(cveId),
        queryFn: () => api.getCVE(cveId),
        staleTime: 10 * 60 * 1000,
      });
    },
  };
}

// =============================================================================
// CVE Utilities
// =============================================================================

export function getSeverityColor(severity: string | null | undefined): string {
  switch (severity?.toUpperCase()) {
    case 'CRITICAL':
      return 'bg-red-500 text-white';
    case 'HIGH':
      return 'bg-orange-500 text-white';
    case 'MEDIUM':
      return 'bg-yellow-500 text-black';
    case 'LOW':
      return 'bg-blue-500 text-white';
    case 'NONE':
      return 'bg-gray-500 text-white';
    default:
      return 'bg-gray-400 text-white';
  }
}

export function getSeverityBorderColor(severity: string | null | undefined): string {
  switch (severity?.toUpperCase()) {
    case 'CRITICAL':
      return 'border-red-500';
    case 'HIGH':
      return 'border-orange-500';
    case 'MEDIUM':
      return 'border-yellow-500';
    case 'LOW':
      return 'border-blue-500';
    default:
      return 'border-gray-400';
  }
}

export function formatCVSSScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return 'N/A';
  return score.toFixed(1);
}

export function getCVELink(cveId: string): string {
  return `https://nvd.nist.gov/vuln/detail/${cveId}`;
}

export function getMitreLink(cveId: string): string {
  return `https://cve.mitre.org/cgi-bin/cvename.cgi?name=${cveId}`;
}

export function getExploitDBLink(cveId: string): string {
  return `https://www.exploit-db.com/search?cve=${cveId}`;
}

export function parseCVSSVector(vector: string | null | undefined): Record<string, string> | null {
  if (!vector) return null;
  
  const parts = vector.split('/');
  const result: Record<string, string> = {};
  
  for (const part of parts) {
    const [key, value] = part.split(':');
    if (key && value) {
      result[key] = value;
    }
  }
  
  return result;
}

export function isValidCVEId(cveId: string): boolean {
  const cvePattern = /^CVE-\d{4}-\d{4,}$/i;
  return cvePattern.test(cveId);
}
