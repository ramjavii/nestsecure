'use client';

import { useQuery } from '@tanstack/react-query';
import { Wifi, WifiOff, AlertCircle, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Badge } from '@/components/ui/badge';

interface BackendStatus {
  status: string;
  timestamp: string;
  version: string;
  environment: string;
}

function getApiBaseUrl(): string {
  if (typeof window !== 'undefined') {
    return process.env.NEXT_PUBLIC_BROWSER_API_URL || 
           process.env.NEXT_PUBLIC_API_URL || 
           'http://localhost:8000';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

async function checkBackendHealth(): Promise<BackendStatus> {
  const baseUrl = getApiBaseUrl().replace('/api/v1', '');
  const response = await fetch(`${baseUrl}/health`, {
    method: 'GET',
    cache: 'no-store',
  });
  
  if (!response.ok) {
    throw new Error('Backend no disponible');
  }
  
  return response.json();
}

interface ConnectionStatusProps {
  className?: string;
  showDetails?: boolean;
}

export function ConnectionStatus({ className, showDetails = false }: ConnectionStatusProps) {
  const { data, isLoading, error, isSuccess } = useQuery({
    queryKey: ['backend-health'],
    queryFn: checkBackendHealth,
    refetchInterval: 30000, // Check every 30 seconds
    retry: 1,
    staleTime: 10000,
  });

  const getStatusInfo = () => {
    if (isLoading) {
      return {
        icon: Wifi,
        color: 'text-yellow-500',
        bgColor: 'bg-yellow-100 dark:bg-yellow-900/30',
        label: 'Conectando...',
        animate: true,
      };
    }
    
    if (error || !isSuccess) {
      return {
        icon: WifiOff,
        color: 'text-red-500',
        bgColor: 'bg-red-100 dark:bg-red-900/30',
        label: 'Desconectado',
        animate: false,
      };
    }
    
    return {
      icon: CheckCircle,
      color: 'text-green-500',
      bgColor: 'bg-green-100 dark:bg-green-900/30',
      label: 'Conectado',
      animate: false,
    };
  };

  const status = getStatusInfo();
  const StatusIcon = status.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className={cn('flex items-center gap-2', className)}>
            <Badge 
              variant="outline" 
              className={cn(
                status.bgColor, 
                status.color, 
                'border-0 cursor-pointer'
              )}
            >
              <StatusIcon 
                className={cn(
                  'h-3 w-3 mr-1',
                  status.animate && 'animate-pulse'
                )} 
              />
              {showDetails && status.label}
            </Badge>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" align="end">
          <div className="text-xs space-y-1">
            <div className="font-medium">{status.label}</div>
            {data && (
              <>
                <div>Versión: {data.version}</div>
                <div>Entorno: {data.environment}</div>
              </>
            )}
            {error && (
              <div className="text-red-500">
                Error: No se puede conectar con el backend
              </div>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * Componente simple de punto de estado
 */
export function ConnectionDot({ className }: { className?: string }) {
  const { isLoading, error, isSuccess } = useQuery({
    queryKey: ['backend-health'],
    queryFn: checkBackendHealth,
    refetchInterval: 30000,
    retry: 1,
    staleTime: 10000,
  });

  const getColor = () => {
    if (isLoading) return 'bg-yellow-500 animate-pulse';
    if (error || !isSuccess) return 'bg-red-500';
    return 'bg-green-500';
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div 
            className={cn(
              'h-2 w-2 rounded-full cursor-pointer',
              getColor(),
              className
            )} 
          />
        </TooltipTrigger>
        <TooltipContent>
          <span className="text-xs">
            {isLoading && 'Conectando con backend...'}
            {error && 'Backend desconectado'}
            {isSuccess && 'Backend conectado'}
          </span>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
