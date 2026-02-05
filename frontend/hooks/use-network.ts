// =============================================================================
// NESTSECURE - Hook para validación de red
// =============================================================================
/**
 * Hook para validar targets de escaneo.
 * 
 * Valida que los targets sean redes privadas (RFC 1918) antes de crear scans.
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

/**
 * Regex para validación local de IP/CIDR (antes de llamar al servidor)
 */
const IP_REGEX = /^(\d{1,3}\.){3}\d{1,3}$/;
const CIDR_REGEX = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/;

/**
 * Rangos de IPs privadas para validación local rápida
 */
const PRIVATE_RANGES = [
  { start: [10, 0, 0, 0], end: [10, 255, 255, 255] },       // 10.0.0.0/8
  { start: [172, 16, 0, 0], end: [172, 31, 255, 255] },     // 172.16.0.0/12
  { start: [192, 168, 0, 0], end: [192, 168, 255, 255] },   // 192.168.0.0/16
  { start: [127, 0, 0, 0], end: [127, 255, 255, 255] },     // 127.0.0.0/8
];

/**
 * Resultado de validación
 */
export interface TargetValidation {
  valid: boolean;
  target: string;
  type: 'ip' | 'cidr' | null;
  error: string | null;
  info?: Record<string, unknown>;
}

/**
 * Valida localmente si una IP es privada (sin llamar al servidor)
 * Útil para validación instantánea en el UI
 */
export function isPrivateIPLocal(ip: string): boolean {
  if (!IP_REGEX.test(ip)) return false;
  
  const parts = ip.split('.').map(Number);
  if (parts.some(p => p < 0 || p > 255)) return false;
  
  return PRIVATE_RANGES.some(range => {
    for (let i = 0; i < 4; i++) {
      if (parts[i] < range.start[i] || parts[i] > range.end[i]) {
        // Verificar si está antes del rango
        if (parts[i] < range.start[i]) return false;
        // Si está después, verificar siguiente octeto
        if (parts[i] > range.end[i]) return false;
      }
    }
    return true;
  });
}

/**
 * Validación rápida local de formato de target
 */
export function isValidTargetFormat(target: string): boolean {
  const trimmed = target.trim();
  return IP_REGEX.test(trimmed) || CIDR_REGEX.test(trimmed);
}

/**
 * Hook para validar un target (con llamada al servidor)
 */
export function useValidateTarget() {
  return useMutation({
    mutationFn: (target: string) => api.validateTarget(target),
    mutationKey: ['network', 'validate'],
  });
}

/**
 * Hook para validar múltiples targets
 */
export function useValidateMultipleTargets() {
  return useMutation({
    mutationFn: (targets: string[]) => api.validateMultipleTargets(targets),
    mutationKey: ['network', 'validate-multiple'],
  });
}

/**
 * Hook para obtener información de una red CIDR
 */
export function useNetworkInfo(cidr: string) {
  return useQuery({
    queryKey: ['network', 'info', cidr],
    queryFn: () => api.getNetworkInfo(cidr),
    enabled: CIDR_REGEX.test(cidr),
    staleTime: 1000 * 60 * 60, // 1 hora
  });
}

/**
 * Hook para obtener los rangos de IPs privadas permitidos
 */
export function usePrivateRanges() {
  return useQuery({
    queryKey: ['network', 'private-ranges'],
    queryFn: () => api.getPrivateRanges(),
    staleTime: Infinity, // Nunca caduca (son constantes)
  });
}

/**
 * Función helper para validar targets localmente antes de enviar al servidor
 * Retorna errores inmediatos si el formato es inválido
 */
export function validateTargetLocally(target: string): TargetValidation {
  const trimmed = target.trim();
  
  if (!trimmed) {
    return {
      valid: false,
      target: trimmed,
      type: null,
      error: 'Target cannot be empty',
    };
  }
  
  // Verificar si es CIDR
  if (trimmed.includes('/')) {
    if (!CIDR_REGEX.test(trimmed)) {
      return {
        valid: false,
        target: trimmed,
        type: 'cidr',
        error: 'Invalid CIDR format. Expected: x.x.x.x/xx',
      };
    }
    
    // Verificar que los números estén en rango
    const [ip, prefix] = trimmed.split('/');
    const parts = ip.split('.').map(Number);
    const prefixNum = Number(prefix);
    
    if (parts.some(p => p < 0 || p > 255)) {
      return {
        valid: false,
        target: trimmed,
        type: 'cidr',
        error: 'Invalid IP octets. Each must be 0-255.',
      };
    }
    
    if (prefixNum < 0 || prefixNum > 32) {
      return {
        valid: false,
        target: trimmed,
        type: 'cidr',
        error: 'Invalid prefix length. Must be 0-32.',
      };
    }
    
    return {
      valid: true, // Formato válido, pero necesita verificación de servidor
      target: trimmed,
      type: 'cidr',
      error: null,
    };
  }
  
  // Verificar si es IP
  if (IP_REGEX.test(trimmed)) {
    const parts = trimmed.split('.').map(Number);
    
    if (parts.some(p => p < 0 || p > 255)) {
      return {
        valid: false,
        target: trimmed,
        type: 'ip',
        error: 'Invalid IP octets. Each must be 0-255.',
      };
    }
    
    // Verificación rápida de IP privada
    if (!isPrivateIPLocal(trimmed)) {
      return {
        valid: false,
        target: trimmed,
        type: 'ip',
        error: 'Public IP addresses are not allowed. Only private IPs (10.x, 172.16-31.x, 192.168.x) are permitted.',
      };
    }
    
    return {
      valid: true,
      target: trimmed,
      type: 'ip',
      error: null,
    };
  }
  
  // No es ni IP ni CIDR - probablemente hostname
  return {
    valid: false,
    target: trimmed,
    type: null,
    error: 'Hostnames are not supported. Please use IP addresses or CIDR notation.',
  };
}

/**
 * Valida múltiples targets localmente
 */
export function validateMultipleTargetsLocally(targets: string[]): {
  valid: boolean;
  results: TargetValidation[];
  validCount: number;
  invalidCount: number;
} {
  const results = targets.map(validateTargetLocally);
  const invalidCount = results.filter(r => !r.valid).length;
  
  return {
    valid: invalidCount === 0,
    results,
    validCount: results.length - invalidCount,
    invalidCount,
  };
}
