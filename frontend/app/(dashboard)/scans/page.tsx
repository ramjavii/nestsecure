'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { Plus, Radar, MoreHorizontal, Eye, StopCircle, Trash2 } from 'lucide-react';
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
import { ProgressBar } from '@/components/shared/progress-bar';
import { TableSkeleton } from '@/components/shared/loading-skeleton';
import { EmptyState } from '@/components/shared/empty-state';
import { ConfirmDialog } from '@/components/shared/confirm-dialog';
import { ScanFormModal } from '@/components/scans/scan-form-modal';
import { useScans, useStopScan, useDeleteScan } from '@/hooks/use-scans';
import { useToast } from '@/hooks/use-toast';
import type { Scan, ScanStatus, ScanType } from '@/types';

const scanTypeLabels: Record<ScanType, string> = {
  discovery: 'Descubrimiento',
  port_scan: 'Escaneo de Puertos',
  service_scan: 'Detección de Servicios',
  vulnerability: 'Vulnerabilidades',
  full: 'Completo',
};

const statusOptions: { value: string; label: string }[] = [
  { value: 'all', label: 'Todos los estados' },
  { value: 'pending', label: 'Pendiente' },
  { value: 'queued', label: 'En cola' },
  { value: 'running', label: 'En ejecución' },
  { value: 'completed', label: 'Completado' },
  { value: 'failed', label: 'Fallido' },
  { value: 'cancelled', label: 'Cancelado' },
];

const typeOptions: { value: string; label: string }[] = [
  { value: 'all', label: 'Todos los tipos' },
  { value: 'discovery', label: 'Descubrimiento' },
  { value: 'port_scan', label: 'Escaneo de Puertos' },
  { value: 'service_scan', label: 'Detección de Servicios' },
  { value: 'vulnerability', label: 'Vulnerabilidades' },
  { value: 'full', label: 'Completo' },
];

// Mock data for demo - Solo se usa cuando no hay conexión con el backend
const ENABLE_MOCK_DATA = false; // Cambiar a true solo para desarrollo sin backend

const mockScans: Scan[] = ENABLE_MOCK_DATA ? [
  {
    id: '1',
    name: 'Escaneo Red Interna',
    description: 'Escaneo completo de la red interna',
    scan_type: 'full',
    status: 'completed',
    progress: 100,
    targets: ['192.168.1.0/24'],
    total_hosts_scanned: 254,
    total_hosts_up: 45,
    total_services_found: 128,
    total_vulnerabilities: 23,
    vuln_critical: 2,
    vuln_high: 5,
    vuln_medium: 8,
    vuln_low: 8,
    started_at: new Date(Date.now() - 3600000).toISOString(),
    completed_at: new Date().toISOString(),
    created_at: new Date(Date.now() - 7200000).toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '2',
    name: 'Escaneo Servidores Web',
    description: 'Análisis de vulnerabilidades en servidores web',
    scan_type: 'vulnerability',
    status: 'running',
    progress: 67,
    targets: ['10.0.0.1', '10.0.0.2', '10.0.0.3'],
    total_hosts_scanned: 3,
    total_hosts_up: 3,
    total_services_found: 12,
    total_vulnerabilities: 5,
    vuln_critical: 1,
    vuln_high: 2,
    vuln_medium: 2,
    vuln_low: 0,
    started_at: new Date(Date.now() - 1800000).toISOString(),
    completed_at: null,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '3',
    name: 'Descubrimiento DMZ',
    description: 'Descubrimiento de hosts en la DMZ',
    scan_type: 'discovery',
    status: 'queued',
    progress: 0,
    targets: ['172.16.0.0/16'],
    total_hosts_scanned: 0,
    total_hosts_up: 0,
    total_services_found: 0,
    total_vulnerabilities: 0,
    vuln_critical: 0,
    vuln_high: 0,
    vuln_medium: 0,
    vuln_low: 0,
    started_at: null,
    completed_at: null,
    created_at: new Date(Date.now() - 600000).toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: '4',
    name: 'Análisis Firewall',
    description: 'Escaneo de puertos del firewall principal',
    scan_type: 'port_scan',
    status: 'failed',
    progress: 34,
    targets: ['192.168.100.1'],
    total_hosts_scanned: 1,
    total_hosts_up: 0,
    total_services_found: 0,
    total_vulnerabilities: 0,
    vuln_critical: 0,
    vuln_high: 0,
    vuln_medium: 0,
    vuln_low: 0,
    started_at: new Date(Date.now() - 86400000).toISOString(),
    completed_at: new Date(Date.now() - 82800000).toISOString(),
    created_at: new Date(Date.now() - 90000000).toISOString(),
    updated_at: new Date(Date.now() - 82800000).toISOString(),
  },
  {
    id: '5',
    name: 'Escaneo Programado Semanal',
    description: 'Escaneo automático semanal',
    scan_type: 'service_scan',
    status: 'pending',
    progress: 0,
    targets: ['192.168.0.0/16'],
    total_hosts_scanned: 0,
    total_hosts_up: 0,
    total_services_found: 0,
    total_vulnerabilities: 0,
    vuln_critical: 0,
    vuln_high: 0,
    vuln_medium: 0,
    vuln_low: 0,
    started_at: null,
    completed_at: null,
    created_at: new Date(Date.now() - 172800000).toISOString(),
    updated_at: new Date().toISOString(),
  },
] : [];

export default function ScansPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    type: 'stop' | 'delete';
    scanId: string;
    scanName: string;
  }>({ open: false, type: 'stop', scanId: '', scanName: '' });

  const { data: scans, isLoading, error } = useScans();
  const stopScan = useStopScan();
  const deleteScan = useDeleteScan();
  const { toast } = useToast();

  // Usar datos del backend, o mock data solo si está habilitado
  const data = scans || (ENABLE_MOCK_DATA ? mockScans : []);

  const filteredScans = useMemo(() => {
    return data.filter((scan) => {
      const matchesStatus = statusFilter === 'all' || scan.status === statusFilter;
      const matchesType = typeFilter === 'all' || scan.scan_type === typeFilter;
      const matchesSearch =
        !search ||
        scan.name.toLowerCase().includes(search.toLowerCase()) ||
        scan.targets.some((t) => t.toLowerCase().includes(search.toLowerCase()));
      
      return matchesStatus && matchesType && matchesSearch;
    });
  }, [data, statusFilter, typeFilter, search]);

  const handleStopScan = async () => {
    try {
      await stopScan.mutateAsync(confirmDialog.scanId);
      toast({
        title: 'Escaneo detenido',
        description: `El escaneo "${confirmDialog.scanName}" ha sido detenido.`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'No se pudo detener el escaneo.',
        variant: 'destructive',
      });
    }
  };

  const handleDeleteScan = async () => {
    try {
      await deleteScan.mutateAsync(confirmDialog.scanId);
      toast({
        title: 'Escaneo eliminado',
        description: `El escaneo "${confirmDialog.scanName}" ha sido eliminado.`,
      });
    } catch (error) {
      toast({
        title: 'Error',
        description: 'No se pudo eliminar el escaneo.',
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Escaneos"
        description="Gestiona y monitorea los escaneos de seguridad"
        actions={
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Nuevo Escaneo
          </Button>
        }
      />

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <SearchInput
              value={search}
              onChange={setSearch}
              placeholder="Buscar por nombre o target..."
              className="flex-1"
            />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-48">
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
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full sm:w-48">
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
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <TableSkeleton rows={5} columns={7} />
          ) : filteredScans.length === 0 ? (
            <EmptyState
              icon={Radar}
              title="No hay escaneos"
              description={
                search || statusFilter !== 'all' || typeFilter !== 'all'
                  ? 'No se encontraron escaneos con los filtros seleccionados.'
                  : 'Aún no has creado ningún escaneo.'
              }
              action={
                !search && statusFilter === 'all' && typeFilter === 'all'
                  ? {
                      label: 'Crear escaneo',
                      onClick: () => setIsModalOpen(true),
                    }
                  : undefined
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Progreso</TableHead>
                  <TableHead>Targets</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredScans.map((scan) => (
                  <TableRow key={scan.id}>
                    <TableCell>
                      <Link
                        href={`/scans/${scan.id}`}
                        className="font-medium hover:text-primary transition-colors"
                      >
                        {scan.name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {scanTypeLabels[scan.scan_type]}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={scan.status} size="sm" />
                    </TableCell>
                    <TableCell className="w-32">
                      <ProgressBar
                        value={scan.progress}
                        size="sm"
                        showLabel
                        animated={scan.status === 'running'}
                        variant={
                          scan.status === 'completed'
                            ? 'success'
                            : scan.status === 'failed'
                            ? 'danger'
                            : 'default'
                        }
                      />
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {scan.targets.length} target{scan.targets.length !== 1 ? 's' : ''}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDistanceToNow(new Date(scan.created_at), {
                        addSuffix: true,
                        locale: es,
                      })}
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
                            <Link href={`/scans/${scan.id}`}>
                              <Eye className="mr-2 h-4 w-4" />
                              Ver detalles
                            </Link>
                          </DropdownMenuItem>
                          {scan.status === 'running' && (
                            <DropdownMenuItem
                              onClick={() =>
                                setConfirmDialog({
                                  open: true,
                                  type: 'stop',
                                  scanId: scan.id,
                                  scanName: scan.name,
                                })
                              }
                            >
                              <StopCircle className="mr-2 h-4 w-4" />
                              Detener
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() =>
                              setConfirmDialog({
                                open: true,
                                type: 'delete',
                                scanId: scan.id,
                                scanName: scan.name,
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
      <ScanFormModal open={isModalOpen} onOpenChange={setIsModalOpen} />

      <ConfirmDialog
        open={confirmDialog.open}
        onOpenChange={(open) => setConfirmDialog({ ...confirmDialog, open })}
        title={confirmDialog.type === 'stop' ? 'Detener escaneo' : 'Eliminar escaneo'}
        description={
          confirmDialog.type === 'stop'
            ? `¿Estás seguro de que deseas detener el escaneo "${confirmDialog.scanName}"? Esta acción no se puede deshacer.`
            : `¿Estás seguro de que deseas eliminar el escaneo "${confirmDialog.scanName}"? Esta acción no se puede deshacer.`
        }
        confirmLabel={confirmDialog.type === 'stop' ? 'Detener' : 'Eliminar'}
        variant="destructive"
        onConfirm={confirmDialog.type === 'stop' ? handleStopScan : handleDeleteScan}
      />
    </div>
  );
}
