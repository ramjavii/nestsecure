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
