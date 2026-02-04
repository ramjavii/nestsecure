'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2 } from 'lucide-react';
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
import { useCreateScan } from '@/hooks/use-scans';
import { useToast } from '@/hooks/use-toast';
import type { ScanType } from '@/types';

const scanSchema = z.object({
  name: z.string().min(3, 'El nombre debe tener al menos 3 caracteres'),
  description: z.string().optional(),
  scan_type: z.enum(['discovery', 'port_scan', 'service_scan', 'vulnerability', 'full']),
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

const scanTypes: { value: ScanType; label: string; description: string }[] = [
  { value: 'discovery', label: 'Descubrimiento', description: 'Detecta hosts activos en la red' },
  { value: 'port_scan', label: 'Escaneo de Puertos', description: 'Identifica puertos abiertos' },
  { value: 'service_scan', label: 'Detección de Servicios', description: 'Identifica servicios y versiones' },
  { value: 'vulnerability', label: 'Vulnerabilidades', description: 'Busca vulnerabilidades conocidas' },
  { value: 'full', label: 'Completo', description: 'Escaneo completo de la red' },
];

export function ScanFormModal({ open, onOpenChange }: ScanFormModalProps) {
  const [isScheduled, setIsScheduled] = useState(false);
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

  const onSubmit = async (data: ScanFormData) => {
    try {
      const targets = data.targets
        .split('\n')
        .map((t) => t.trim())
        .filter((t) => t.length > 0);

      await createScan.mutateAsync({
        name: data.name,
        description: data.description,
        scan_type: data.scan_type,
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
              onValueChange={(value) => setValue('scan_type', value as ScanType)}
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
              placeholder="192.168.1.0/24&#10;10.0.0.1&#10;ejemplo.com"
              rows={3}
              {...register('targets')}
            />
            <p className="text-xs text-muted-foreground">
              Ingresa IPs, rangos CIDR o hostnames (uno por línea)
            </p>
            {errors.targets && (
              <p className="text-sm text-destructive">{errors.targets.message}</p>
            )}
          </div>

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
            <Button type="submit" disabled={createScan.isPending}>
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
