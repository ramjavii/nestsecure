'use client';

import { useState, useEffect, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useCreateScan } from '@/hooks/use-scans';
import { useToast } from '@/hooks/use-toast';
import { validateMultipleTargetsLocally } from '@/hooks/use-network';
import type { ScanType } from '@/types';

const scanSchema = z.object({
  name: z.string().min(3, 'El nombre debe tener al menos 3 caracteres'),
  description: z.string().optional(),
  scan_type: z.enum(['discovery', 'port_scan', 'service_scan', 'vulnerability', 'full', 'nuclei', 'zap', 'openvas']),
  targets: z.string().min(1, 'Debes especificar al menos un target'),
  port_range: z.string().optional(),
  scheduled: z.boolean().default(false),
  cron_expression: z.string().optional(),
});

type ScanFormData = z.infer<typeof scanSchema>;

interface ScanFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const scanTypes: { value: ScanFormData['scan_type']; label: string; description: string }[] = [
  { value: 'discovery', label: 'Descubrimiento', description: 'Detecta hosts activos en la red' },
  { value: 'port_scan', label: 'Puertos y Servicios', description: 'Identifica puertos abiertos, servicios y versiones' },
  { value: 'service_scan', label: 'Detección de Servicios', description: 'Identifica servicios y versiones en detalle' },
  { value: 'vulnerability', label: 'Vulnerabilidades (Nmap)', description: 'Busca vulnerabilidades conocidas con Nmap NSE' },
  { value: 'full', label: 'Completo', description: 'Escaneo completo: todos los puertos (65535)' },
  { value: 'nuclei', label: 'Nuclei', description: 'Escaneo de vulnerabilidades con templates Nuclei' },
  { value: 'zap', label: 'OWASP ZAP', description: 'Escaneo DAST para aplicaciones web' },
  { value: 'openvas', label: 'OpenVAS', description: 'Escaneo completo con OpenVAS/GVM' },
];

export function ScanFormModal({ open, onOpenChange }: ScanFormModalProps) {
  const [isScheduled, setIsScheduled] = useState(false);
  const [targetValidation, setTargetValidation] = useState<{
    valid: boolean;
    errors: string[];
    validCount: number;
    invalidCount: number;
  } | null>(null);
  const createScan = useCreateScan();
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<ScanFormData>({
    resolver: zodResolver(scanSchema),
    defaultValues: {
      scan_type: 'discovery',
      scheduled: false,
    },
  });

  const scanType = watch('scan_type');
  const targetsValue = watch('targets');

  // Obtener información del tipo de scan
  const getScanTypeInfo = (type: string) => {
    const info: Record<string, { inputFormat: string; example: string; requiresProtocol: boolean }> = {
      nuclei: {
        inputFormat: 'URLs con protocolo http:// o https://',
        example: 'http://192.168.15.50\nhttps://example.com',
        requiresProtocol: true,
      },
      zap: {
        inputFormat: 'URLs web completas con protocolo',
        example: 'http://192.168.15.50/app\nhttps://example.com/login',
        requiresProtocol: true,
      },
      openvas: {
        inputFormat: 'IPs, rangos CIDR, o hostnames',
        example: '192.168.15.0/24\n192.168.15.50\nexample.com',
        requiresProtocol: false,
      },
      discovery: {
        inputFormat: 'IPs o rangos CIDR',
        example: '192.168.1.0/24\n10.0.0.1',
        requiresProtocol: false,
      },
      port_scan: {
        inputFormat: 'IPs o rangos CIDR',
        example: '192.168.1.0/24\n10.0.0.1',
        requiresProtocol: false,
      },
      service_scan: {
        inputFormat: 'IPs o rangos CIDR',
        example: '192.168.1.0/24\n10.0.0.1',
        requiresProtocol: false,
      },
      vulnerability: {
        inputFormat: 'IPs o rangos CIDR',
        example: '192.168.1.0/24\n10.0.0.1',
        requiresProtocol: false,
      },
      full: {
        inputFormat: 'IPs o rangos CIDR',
        example: '192.168.1.0/24\n10.0.0.1',
        requiresProtocol: false,
      },
    };
    return info[type] || info['discovery'];
  };

  const currentScanInfo = getScanTypeInfo(scanType);

  // Validar targets cuando cambian
  const validateTargets = useCallback((value: string, scanType: string) => {
    if (!value || !value.trim()) {
      setTargetValidation(null);
      return;
    }

    const targets = value
      .split('\n')
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    if (targets.length === 0) {
      setTargetValidation(null);
      return;
    }

    const errors: string[] = [];
    let validCount = 0;
    const scanInfo = getScanTypeInfo(scanType);

    targets.forEach((target) => {
      if (scanInfo.requiresProtocol) {
        // ZAP y Nuclei requieren URLs con protocolo
        if (!target.startsWith('http://') && !target.startsWith('https://')) {
          errors.push(`${target}: debe incluir protocolo http:// o https://`);
          return;
        }
        // Validar que sea una URL válida
        try {
          new URL(target);
          validCount++;
        } catch {
          errors.push(`${target}: URL inválida`);
        }
      } else {
        // OpenVAS, Nmap, etc: validar IP/CIDR/hostname
        const result = validateMultipleTargetsLocally([target]);
        if (result.valid) {
          validCount++;
        } else {
          const targetError = result.results.find(r => r.target === target);
          if (targetError && !targetError.valid) {
            errors.push(`${target}: ${targetError.error}`);
          }
        }
      }
    });

    setTargetValidation({
      valid: errors.length === 0,
      errors,
      validCount,
      invalidCount: errors.length,
    });
  }, []);

  // Efecto para validar cuando cambian los targets o el tipo de scan
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      validateTargets(targetsValue || '', scanType);
    }, 300); // Debounce 300ms

    return () => clearTimeout(timeoutId);
  }, [targetsValue, scanType, validateTargets]);

  const onSubmit = async (data: ScanFormData) => {
    try {
      const targets = data.targets
        .split('\n')
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      await createScan.mutateAsync({
        name: data.name,
        description: data.description,
        scan_type: data.scan_type as ScanType,
        targets,
        port_range: data.port_range,
        scheduled: data.scheduled,
        cron_expression: data.cron_expression,
      });

      toast({
        title: 'Escaneo creado',
        description: 'El escaneo ha sido iniciado correctamente.',
      });

      reset();
      onOpenChange(false);
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'No se pudo crear el escaneo',
        variant: 'destructive',
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Nuevo Escaneo</DialogTitle>
          <DialogDescription>
            Configura los parámetros del escaneo de seguridad
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Nombre del escaneo</Label>
            <Input
              id="name"
              placeholder="Escaneo Red Interna"
              {...register('name')}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Descripción (opcional)</Label>
            <Textarea
              id="description"
              placeholder="Descripción del escaneo..."
              rows={2}
              {...register('description')}
            />
          </div>

          <div className="space-y-2">
            <Label>Tipo de escaneo</Label>
            <Select
              value={scanType}
              onValueChange={(value) => setValue('scan_type', value as 'discovery' | 'port_scan' | 'vulnerability' | 'full')}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecciona el tipo" />
              </SelectTrigger>
              <SelectContent>
                {scanTypes.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    <div className="flex flex-col">
                      <span>{type.label}</span>
                      <span className="text-xs text-muted-foreground">{type.description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="targets">Targets</Label>
            <Textarea
              id="targets"
              placeholder={currentScanInfo.example}
              rows={3}
              {...register('targets')}
              className={targetValidation && !targetValidation.valid ? 'border-destructive' : ''}
            />
            <p className="text-xs text-muted-foreground">
              {currentScanInfo.inputFormat}
            </p>
            
            {/* Mostrar estado de validación */}
            {targetValidation && (
              <div className="mt-2">
                {targetValidation.valid ? (
                  <div className="flex items-center gap-2 text-sm text-green-600">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>{targetValidation.validCount} target(s) válido(s)</span>
                  </div>
                ) : (
                  <Alert variant="destructive" className="py-2">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <div className="text-sm">
                        <p className="font-medium">
                          {targetValidation.invalidCount} target(s) inválido(s):
                        </p>
                        <ul className="mt-1 list-disc list-inside">
                          {targetValidation.errors.slice(0, 3).map((error, i) => (
                            <li key={i} className="text-xs">{error}</li>
                          ))}
                          {targetValidation.errors.length > 3 && (
                            <li className="text-xs">
                              ... y {targetValidation.errors.length - 3} más
                            </li>
                          )}
                        </ul>
                      </div>
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            )}
            
            {errors.targets && (
              <p className="text-sm text-destructive">{errors.targets.message}</p>
            )}
          </div>

          {/* Info específica según tipo de scan */}
          <Alert className="py-2">
            <Info className="h-4 w-4" />
            <AlertDescription className="text-xs">
              {currentScanInfo.requiresProtocol ? (
                <>
                  <strong>{scanType === 'zap' ? 'OWASP ZAP' : 'Nuclei'}</strong> requiere URLs completas con protocolo.
                  Ejemplo: http://192.168.15.50 o https://app.example.com
                </>
              ) : (
                <>
                  Por seguridad, solo se permiten escaneos a redes privadas (RFC 1918).
                  Las IPs públicas están bloqueadas.
                </>
              )}
            </AlertDescription>
          </Alert>

          <div className="space-y-2">
            <Label htmlFor="port_range">Rango de puertos (opcional)</Label>
            <Input
              id="port_range"
              placeholder="1-1024 o 22,80,443,8080"
              {...register('port_range')}
            />
            <p className="text-xs text-muted-foreground">
              Deja vacío para usar el rango por defecto
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="scheduled"
              checked={isScheduled}
              onCheckedChange={(checked) => {
                setIsScheduled(checked as boolean);
                setValue('scheduled', checked as boolean);
              }}
            />
            <Label htmlFor="scheduled" className="text-sm font-normal">
              Programar escaneo
            </Label>
          </div>

          {isScheduled && (
            <div className="space-y-2">
              <Label htmlFor="cron_expression">Expresión Cron</Label>
              <Input
                id="cron_expression"
                placeholder="0 2 * * *"
                {...register('cron_expression')}
              />
              <p className="text-xs text-muted-foreground">
                Ejemplo: 0 2 * * * (cada día a las 2:00 AM)
              </p>
            </div>
          )}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={createScan.isPending}
            >
              Cancelar
            </Button>
            <Button 
              type="submit" 
              disabled={createScan.isPending || (targetValidation !== null && !targetValidation.valid)}
            >
              {createScan.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Iniciar Escaneo
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
