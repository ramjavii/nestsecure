'use client';

import { useEffect } from 'react';
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
import { useCreateAsset, useUpdateAsset } from '@/hooks/use-assets';
import { useToast } from '@/hooks/use-toast';
import type { Asset, AssetType, Criticality } from '@/types';

const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;

const assetSchema = z.object({
  ip_address: z.string().regex(ipRegex, 'Dirección IP inválida'),
  hostname: z.string().optional(),
  mac_address: z.string().regex(macRegex, 'Dirección MAC inválida').optional().or(z.literal('')),
  operating_system: z.string().optional(),
  asset_type: z.enum(['server', 'workstation', 'network_device', 'iot', 'other']),
  criticality: z.enum(['critical', 'high', 'medium', 'low']),
  description: z.string().optional(),
});

type AssetFormData = z.infer<typeof assetSchema>;

interface AssetFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  asset?: Asset; // Si se proporciona, es modo edición
  mode?: 'create' | 'edit';
}

const assetTypes: { value: AssetType; label: string }[] = [
  { value: 'server', label: 'Servidor' },
  { value: 'workstation', label: 'Estación de trabajo' },
  { value: 'network_device', label: 'Dispositivo de red' },
  { value: 'iot', label: 'IoT' },
  { value: 'other', label: 'Otro' },
];

const criticalities: { value: Criticality; label: string }[] = [
  { value: 'critical', label: 'Crítico' },
  { value: 'high', label: 'Alto' },
  { value: 'medium', label: 'Medio' },
  { value: 'low', label: 'Bajo' },
];

export function AssetFormModal({ open, onOpenChange, asset, mode = 'create' }: AssetFormModalProps) {
  const isEdit = mode === 'edit' && asset;
  const createAsset = useCreateAsset();
  const updateAsset = useUpdateAsset();
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<AssetFormData>({
    resolver: zodResolver(assetSchema),
    defaultValues: {
      asset_type: 'server',
      criticality: 'medium',
    },
  });

  // Cargar datos del asset en modo edición
  useEffect(() => {
    if (isEdit && asset) {
      reset({
        ip_address: asset.ip_address,
        hostname: asset.hostname || '',
        mac_address: asset.mac_address || '',
        operating_system: asset.operating_system || '',
        asset_type: asset.asset_type,
        criticality: asset.criticality,
        description: asset.description || '',
      });
    } else if (!isEdit) {
      reset({
        ip_address: '',
        hostname: '',
        mac_address: '',
        operating_system: '',
        asset_type: 'server',
        criticality: 'medium',
        description: '',
      });
    }
  }, [isEdit, asset, reset]);

  const assetType = watch('asset_type');
  const criticality = watch('criticality');

  const isPending = createAsset.isPending || updateAsset.isPending;

  const onSubmit = async (data: AssetFormData) => {
    try {
      const payload = {
        ip_address: data.ip_address,
        hostname: data.hostname || undefined,
        mac_address: data.mac_address || undefined,
        operating_system: data.operating_system || undefined,
        asset_type: data.asset_type,
        criticality: data.criticality,
        description: data.description || undefined,
      };

      if (isEdit && asset) {
        await updateAsset.mutateAsync({ id: asset.id, payload });
        toast({
          title: 'Asset actualizado',
          description: 'El asset ha sido actualizado correctamente.',
        });
      } else {
        await createAsset.mutateAsync(payload);
        toast({
          title: 'Asset creado',
          description: 'El asset ha sido agregado correctamente.',
        });
      }

      reset();
      onOpenChange(false);
    } catch (error) {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : `No se pudo ${isEdit ? 'actualizar' : 'crear'} el asset`,
        variant: 'destructive',
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Editar Asset' : 'Agregar Asset'}</DialogTitle>
          <DialogDescription>
            {isEdit 
              ? 'Modifica la información del asset seleccionado'
              : 'Agrega un nuevo asset a tu inventario de infraestructura'
            }
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ip_address">Dirección IP *</Label>
              <Input
                id="ip_address"
                placeholder="192.168.1.100"
                {...register('ip_address')}
              />
              {errors.ip_address && (
                <p className="text-sm text-destructive">{errors.ip_address.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="hostname">Hostname</Label>
              <Input
                id="hostname"
                placeholder="servidor-web-01"
                {...register('hostname')}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="mac_address">Dirección MAC</Label>
              <Input
                id="mac_address"
                placeholder="00:1A:2B:3C:4D:5E"
                {...register('mac_address')}
              />
              {errors.mac_address && (
                <p className="text-sm text-destructive">{errors.mac_address.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="operating_system">Sistema Operativo</Label>
              <Input
                id="operating_system"
                placeholder="Ubuntu 22.04"
                {...register('operating_system')}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Tipo de Asset *</Label>
              <Select
                value={assetType}
                onValueChange={(value) => setValue('asset_type', value as AssetType)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona el tipo" />
                </SelectTrigger>
                <SelectContent>
                  {assetTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Criticidad *</Label>
              <Select
                value={criticality}
                onValueChange={(value) => setValue('criticality', value as Criticality)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona criticidad" />
                </SelectTrigger>
                <SelectContent>
                  {criticalities.map((crit) => (
                    <SelectItem key={crit.value} value={crit.value}>
                      {crit.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Descripción</Label>
            <Textarea
              id="description"
              placeholder="Descripción del asset..."
              rows={3}
              {...register('description')}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isPending}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {isEdit ? 'Guardar cambios' : 'Agregar Asset'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
