'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { ReportType, ReportFormat, ReportStatus } from '@/types';
import { toast } from 'sonner';

/**
 * Hook para listar reportes con filtros y paginación
 */
export function useReports(params?: {
  report_type?: string;
  status?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: () => api.getReports(params),
    refetchInterval: (query) => {
      // Si hay reportes pendientes o generando, hacer polling
      const data = query.state.data;
      if (!data?.reports) return false;
      
      const hasPending = data.reports.some(
        (r) => r.status === 'pending' || r.status === 'generating'
      );
      return hasPending ? 5000 : false;
    },
  });
}

/**
 * Hook para obtener un reporte específico
 */
export function useReport(id: string) {
  return useQuery({
    queryKey: ['report', id],
    queryFn: () => api.getReport(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const report = query.state.data;
      if (!report) return false;
      
      // Polling mientras está en proceso
      if (report.status === 'pending' || report.status === 'generating') {
        return 3000;
      }
      return false;
    },
  });
}

/**
 * Hook para generar nuevo reporte
 */
export function useGenerateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: {
      name: string;
      report_type: ReportType;
      format: ReportFormat;
      description?: string;
      date_from?: string;
      date_to?: string;
      severity_filter?: string[];
      status_filter?: string[];
      asset_ids?: string[];
    }) => api.generateReport(payload),
    onSuccess: (data) => {
      toast.success(data.message || 'Reporte en cola de generación');
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Error al generar reporte');
    },
  });
}

/**
 * Hook para descargar reporte
 */
export function useDownloadReport() {
  return useMutation({
    mutationFn: async (report: { id: string; name: string; format: string }) => {
      const blob = await api.downloadReport(report.id);
      
      // Crear link de descarga
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${report.name.replace(/\s+/g, '_')}.${report.format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      return { success: true };
    },
    onSuccess: () => {
      toast.success('Reporte descargado');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Error al descargar reporte');
    },
  });
}

/**
 * Hook para eliminar reporte
 */
export function useDeleteReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => api.deleteReport(id),
    onSuccess: () => {
      toast.success('Reporte eliminado');
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Error al eliminar reporte');
    },
  });
}

// Constantes útiles para forms
export const REPORT_TYPES: Array<{ value: ReportType; label: string; description: string }> = [
  { value: 'executive', label: 'Ejecutivo', description: 'Resumen de alto nivel para gerencia' },
  { value: 'technical', label: 'Técnico', description: 'Detalles técnicos completos' },
  { value: 'vulnerability', label: 'Vulnerabilidades', description: 'Lista detallada de vulnerabilidades' },
  { value: 'asset_inventory', label: 'Inventario de Assets', description: 'Lista completa de activos' },
  { value: 'scan_summary', label: 'Resumen de Scans', description: 'Historial y resultados de escaneos' },
  { value: 'compliance', label: 'Compliance', description: 'Reporte de cumplimiento' },
];

export const REPORT_FORMATS: Array<{ value: ReportFormat; label: string; icon: string }> = [
  { value: 'pdf', label: 'PDF', icon: '📄' },
  { value: 'xlsx', label: 'Excel', icon: '📊' },
  { value: 'csv', label: 'CSV', icon: '📋' },
  { value: 'json', label: 'JSON', icon: '🔧' },
];

export const REPORT_STATUSES: Record<ReportStatus, { label: string; color: string }> = {
  pending: { label: 'Pendiente', color: 'yellow' },
  generating: { label: 'Generando', color: 'blue' },
  completed: { label: 'Completado', color: 'green' },
  failed: { label: 'Error', color: 'red' },
};
