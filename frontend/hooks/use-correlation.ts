'use client';

/**
 * Hook para correlación de servicios con CVEs
 * 
 * Proporciona funciones para correlacionar servicios detectados
 * con vulnerabilidades conocidas (CVEs) del NVD.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { toast } from 'sonner';

// ===========================================================================
// TYPES
// ===========================================================================

export interface CorrelationResult {
  service_id: string;
  cpe: string | null;
  cpe_confidence: number;
  cves_found: number;
  vulnerabilities_created: number;
  status: 'success' | 'no_cpe' | 'no_cves' | 'error' | 'pending';
  cves: string[];
  error: string | null;
}

export interface ScanCorrelationResult {
  scan_id: string;
  services_processed: number;
  services_with_cpe: number;
  cves_found: number;
  vulnerabilities_created: number;
  status: string;
  services: CorrelationResult[];
}

export interface AssetCorrelationResult {
  asset_id: string;
  services_processed: number;
  cves_found: number;
  vulnerabilities_created: number;
  services: CorrelationResult[];
}

export interface CPEInfo {
  service_id: string;
  port: number;
  protocol: string;
  service_name: string | null;
  product: string | null;
  version: string | null;
  cpe: string | null;
  cpe_source: 'nmap_detected' | 'constructed' | 'none';
  confidence: number;
}

// ===========================================================================
// HOOKS
// ===========================================================================

/**
 * Hook para correlacionar un servicio individual
 */
export function useCorrelateService() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      serviceId,
      autoCreateVuln = true,
      maxCves = 10,
    }: {
      serviceId: string;
      autoCreateVuln?: boolean;
      maxCves?: number;
    }) => {
      return api.correlateService(serviceId, { autoCreateVuln, maxCves });
    },
    onSuccess: (data) => {
      if (data.status === 'success') {
        toast.success(
          `Correlación completada: ${data.cves_found} CVEs encontrados, ` +
          `${data.vulnerabilities_created} vulnerabilidades creadas`
        );
      } else if (data.status === 'no_cpe') {
        toast.warning('No se pudo construir CPE para este servicio');
      } else if (data.status === 'no_cves') {
        toast.info('No se encontraron CVEs para este servicio');
      }
      
      // Invalidar queries relacionadas
      queryClient.invalidateQueries({ queryKey: ['vulnerabilities'] });
      queryClient.invalidateQueries({ queryKey: ['services'] });
    },
    onError: (error) => {
      toast.error(`Error en correlación: ${error.message}`);
    },
  });
}

/**
 * Hook para correlacionar todos los servicios de un scan
 */
export function useCorrelateScan() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      scanId,
      autoCreate = true,
      maxCvesPerService = 10,
    }: {
      scanId: string;
      autoCreate?: boolean;
      maxCvesPerService?: number;
    }) => {
      return api.correlateScan(scanId, { autoCreate, maxCvesPerService });
    },
    onSuccess: (data) => {
      toast.success(
        `Correlación de scan completada:\n` +
        `• ${data.services_processed} servicios procesados\n` +
        `• ${data.services_with_cpe} con CPE válido\n` +
        `• ${data.cves_found} CVEs encontrados\n` +
        `• ${data.vulnerabilities_created} vulnerabilidades creadas`
      );
      
      // Invalidar queries
      queryClient.invalidateQueries({ queryKey: ['scans'] });
      queryClient.invalidateQueries({ queryKey: ['vulnerabilities'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (error) => {
      toast.error(`Error correlacionando scan: ${error.message}`);
    },
  });
}

/**
 * Hook para correlacionar servicios de un asset
 */
export function useCorrelateAsset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      assetId,
      autoCreate = true,
    }: {
      assetId: string;
      autoCreate?: boolean;
    }) => {
      return api.correlateAsset(assetId, autoCreate);
    },
    onSuccess: (data) => {
      toast.success(
        `Asset correlacionado: ${data.cves_found} CVEs, ` +
        `${data.vulnerabilities_created} vulnerabilidades`
      );
      
      queryClient.invalidateQueries({ queryKey: ['assets'] });
      queryClient.invalidateQueries({ queryKey: ['vulnerabilities'] });
    },
    onError: (error) => {
      toast.error(`Error correlacionando asset: ${error.message}`);
    },
  });
}

/**
 * Hook para obtener CPE de un servicio
 */
export function useServiceCPE(serviceId: string | null) {
  return useQuery({
    queryKey: ['service-cpe', serviceId],
    queryFn: async () => {
      if (!serviceId) return null;
      return api.getServiceCPE(serviceId);
    },
    enabled: !!serviceId,
    staleTime: 1000 * 60 * 5, // 5 minutos
  });
}

// ===========================================================================
// UTILITIES
// ===========================================================================

/**
 * Obtiene el color de badge según la confianza del CPE
 */
export function getCPEConfidenceColor(confidence: number): string {
  if (confidence >= 90) return 'bg-green-100 text-green-800';
  if (confidence >= 70) return 'bg-yellow-100 text-yellow-800';
  if (confidence >= 50) return 'bg-orange-100 text-orange-800';
  return 'bg-red-100 text-red-800';
}

/**
 * Obtiene el texto de origen del CPE
 */
export function getCPESourceLabel(source: string): string {
  switch (source) {
    case 'nmap_detected':
      return 'Detectado por Nmap';
    case 'constructed':
      return 'Construido automáticamente';
    case 'none':
      return 'No disponible';
    default:
      return source;
  }
}

/**
 * Formatea el estado de correlación
 */
export function getCorrelationStatusLabel(status: string): {
  label: string;
  variant: 'default' | 'success' | 'warning' | 'destructive';
} {
  switch (status) {
    case 'success':
      return { label: 'Completado', variant: 'success' };
    case 'no_cpe':
      return { label: 'Sin CPE', variant: 'warning' };
    case 'no_cves':
      return { label: 'Sin CVEs', variant: 'default' };
    case 'error':
      return { label: 'Error', variant: 'destructive' };
    case 'pending':
      return { label: 'Pendiente', variant: 'default' };
    default:
      return { label: status, variant: 'default' };
  }
}
