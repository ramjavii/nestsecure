'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: () => api.getDashboardStats(),
  });
}

export function useRecentScans() {
  return useQuery({
    queryKey: ['dashboard', 'recent-scans'],
    queryFn: () => api.getRecentScans(),
  });
}

export function useRecentAssets() {
  return useQuery({
    queryKey: ['dashboard', 'recent-assets'],
    queryFn: () => api.getRecentAssets(),
  });
}

export function useVulnerabilityTrend() {
  return useQuery({
    queryKey: ['dashboard', 'vulnerability-trend'],
    queryFn: () => api.getVulnerabilityTrend(),
  });
}

export function useHealthStatus() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.getHealthStatus(),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

/**
 * Hook for fetching top vulnerabilities for dashboard
 * Fetches critical and high severity vulnerabilities, sorted by severity
 */
export function useTopVulnerabilities(limit: number = 5) {
  return useQuery({
    queryKey: ['dashboard', 'top-vulnerabilities', limit],
    queryFn: async () => {
      // First try critical
      const critical = await api.getVulnerabilities({ 
        severity: 'critical', 
        status: 'open' 
      });
      
      // Then high
      const high = await api.getVulnerabilities({ 
        severity: 'high', 
        status: 'open' 
      });
      
      // Combine and limit
      const combined = [...(critical || []), ...(high || [])];
      return combined.slice(0, limit);
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
