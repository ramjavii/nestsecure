'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { Plus, Server, MoreHorizontal, Eye, Pencil, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { PageHeader } from '@/components/shared/page-header';
import { SearchInput } from '@/components/shared/search-input';
import { StatusBadge } from '@/components/shared/status-badge';
import { CriticalityBadge } from '@/components/shared/criticality-badge';
import { ProgressBar } from '@/components/shared/progress-bar';
import { TableSkeleton } from '@/components/shared/loading-skeleton';
import { EmptyState } from '@/components/shared/empty-state';
import { ConfirmDialog } from '@/components/shared/confirm-dialog';
import { AssetFormModal } from '@/components/assets/asset-form-modal';
import { useAssets, useDeleteAsset } from '@/hooks/use-assets';
import { useToast } from '@/hooks/use-toast';
import type { Asset, AssetType, Criticality, AssetStatus } from '@/types';

const assetTypeLabels: Record<AssetType, string> = {
  server: 'Servidor',
  workstation: 'Estación de trabajo',
  network_device: 'Dispositivo de red',
  iot: 'IoT',
  other: 'Otro',
};

const typeOptions: { value: string; label: string }[] = [
  { value: 'all', label: 'Todos los tipos' },
  { value: 'server', label: 'Servidor' },
  { value: 'workstation', label: 'Estación de trabajo' },
  { value: 'network_device', label: 'Dispositivo de red' },
  { value: 'iot', label: 'IoT' },
  { value: 'other', label: 'Otro' },
];

const criticalityOptions: { value: string; label: string }[] = [
  { value: 'all', label: 'Todas las criticidades' },
  { value: 'critical', label: 'Crítico' },
  { value: 'high', label: 'Alto' },
  { value: 'medium', label: 'Medio' },
  { value: 'low', label: 'Bajo' },
];

const statusOptions: { value: string; label: string }[] = [
  { value: 'all', label: 'Todos los estados' },
  { value: 'active', label: 'Activo' },
  { value: 'inactive', label: 'Inactivo' },
  { value: 'maintenance', label: 'Mantenimiento' },
];\n\n// Production mode - no mock data

export default function AssetsPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editModal, setEditModal] = useState<{
    open: boolean;
    asset: Asset | null;
  }>({ open: false, asset: null });
  const [typeFilter, setTypeFilter] = useState('all');
  const [criticalityFilter, setCriticalityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean;
    assetId: string;
    assetName: string;
  }>({ open: false, assetId: '', assetName: '' });

  const { data: assetsResponse, isLoading, error } = useAssets();
  const deleteAsset = useDeleteAsset();
  const { toast } = useToast();

  // Extraer items de la respuesta paginada
  const data = assetsResponse?.items || [];

  const handleEditAsset = (asset: Asset) => {
    setEditModal({ open: true, asset });
  };

  const filteredAssets = useMemo(() => {
    return data.filter((asset) => {
      const matchesType = typeFilter === 'all' || asset.asset_type === typeFilter;
      const matchesCriticality = criticalityFilter === 'all' || asset.criticality === criticalityFilter;
      const matchesStatus = statusFilter === 'all' || asset.status === statusFilter;
      const matchesSearch =
        !search ||
        asset.ip_address.toLowerCase().includes(search.toLowerCase()) ||
        asset.hostname?.toLowerCase().includes(search.toLowerCase());
      
      return matchesType && matchesCriticality && matchesStatus && matchesSearch;
    });
  }, [data, typeFilter, criticalityFilter, statusFilter, search]);

  const handleDeleteAsset = async () => {
    try {
      await deleteAsset.mutateAsync(deleteDialog.assetId);
      toast({
        title: 'Asset eliminado',
        description: `El asset "${deleteDialog.assetName}" ha sido eliminado.`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'No se pudo eliminar el asset.',
        variant: 'destructive',
      });
    }
  };

  const getRiskScoreVariant = (score: number) => {
    if (score >= 70) return 'danger';
    if (score >= 40) return 'warning';
    return 'success';
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Assets"
        description="Gestiona tu inventario de infraestructura"
        actions={
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Agregar Asset
          </Button>
        }
      />

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col lg:flex-row gap-4">
            <SearchInput
              value={search}
              onChange={setSearch}
              placeholder="Buscar por IP o hostname..."
              className="flex-1"
            />
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full lg:w-48">
                <SelectValue placeholder="Tipo" />
              </SelectTrigger>
              <SelectContent>
                {typeOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={criticalityFilter} onValueChange={setCriticalityFilter}>
              <SelectTrigger className="w-full lg:w-48">
                <SelectValue placeholder="Criticidad" />
              </SelectTrigger>
              <SelectContent>
                {criticalityOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full lg:w-40">
                <SelectValue placeholder="Estado" />
              </SelectTrigger>
              <SelectContent>
                {statusOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <TableSkeleton rows={5} columns={7} />
          ) : filteredAssets.length === 0 ? (
            <EmptyState
              icon={Server}
              title="No hay assets"
              description={
                search || typeFilter !== 'all' || criticalityFilter !== 'all' || statusFilter !== 'all'
                  ? 'No se encontraron assets con los filtros seleccionados.'
                  : 'Aún no has agregado ningún asset.'
              }
              action={
                !search && typeFilter === 'all' && criticalityFilter === 'all' && statusFilter === 'all'
                  ? {
                      label: 'Agregar asset',
                      onClick: () => setIsModalOpen(true),
                    }
                  : undefined
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>IP / Hostname</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Criticidad</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Risk Score</TableHead>
                  <TableHead>Último escaneo</TableHead>
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAssets.map((asset) => (
                  <TableRow key={asset.id}>
                    <TableCell>
                      <Link
                        href={`/assets/${asset.id}`}
                        className="hover:text-primary transition-colors"
                      >
                        <div className="font-mono font-medium">{asset.ip_address}</div>
                        {asset.hostname && (
                          <div className="text-sm text-muted-foreground">{asset.hostname}</div>
                        )}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {assetTypeLabels[asset.asset_type]}
                    </TableCell>
                    <TableCell>
                      <CriticalityBadge criticality={asset.criticality} size="sm" />
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={asset.status} size="sm" />
                    </TableCell>
                    <TableCell className="w-32">
                      <ProgressBar
                        value={asset.risk_score}
                        size="sm"
                        showLabel
                        variant={getRiskScoreVariant(asset.risk_score)}
                      />
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {asset.last_seen_at
                        ? formatDistanceToNow(new Date(asset.last_seen_at), {
                            addSuffix: true,
                            locale: es,
                          })
                        : '-'}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link href={`/assets/${asset.id}`}>
                              <Eye className="mr-2 h-4 w-4" />
                              Ver detalles
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleEditAsset(asset)}>
                            <Pencil className="mr-2 h-4 w-4" />
                            Editar
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() =>
                              setDeleteDialog({
                                open: true,
                                assetId: asset.id,
                                assetName: asset.hostname || asset.ip_address,
                              })
                            }
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Eliminar
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Modals */}
      <AssetFormModal open={isModalOpen} onOpenChange={setIsModalOpen} />
      
      {/* Edit Modal */}
      <AssetFormModal 
        open={editModal.open} 
        onOpenChange={(open) => setEditModal({ ...editModal, open })}
        asset={editModal.asset || undefined}
        mode="edit"
      />

      <ConfirmDialog
        open={deleteDialog.open}
        onOpenChange={(open) => setDeleteDialog({ ...deleteDialog, open })}
        title="Eliminar asset"
        description={`¿Estás seguro de que deseas eliminar el asset "${deleteDialog.assetName}"? Esta acción no se puede deshacer.`}
        confirmLabel="Eliminar"
        variant="destructive"
        onConfirm={handleDeleteAsset}
      />
    </div>
  );
}
