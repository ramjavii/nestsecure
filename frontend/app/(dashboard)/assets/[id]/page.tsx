'use client';

import { useState, use } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { formatDistanceToNow, format } from 'date-fns';
import { es } from 'date-fns/locale';
import {
  ArrowLeft,
  Server,
  Network,
  AlertTriangle,
  Shield,
  Pencil,
  Trash2,
  Radar,
  Activity,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/shared/page-header';
import { StatCard } from '@/components/shared/stat-card';
import { StatusBadge } from '@/components/shared/status-badge';
import { SeverityBadge } from '@/components/shared/severity-badge';
import { CriticalityBadge } from '@/components/shared/criticality-badge';
import { ProgressBar } from '@/components/shared/progress-bar';
import { ConfirmDialog } from '@/components/shared/confirm-dialog';
import { EmptyState } from '@/components/shared/empty-state';
import { useAsset, useAssetServices, useAssetVulnerabilities, useDeleteAsset } from '@/hooks/use-assets';
import { useToast } from '@/hooks/use-toast';
import type { Asset, Service, Vulnerability, Scan } from '@/types';

interface AssetDetailPageProps {
  params: Promise<{ id: string }>;
}

// Empty defaults for production mode
const emptyAsset: Asset = {
  id: '',
  ip_address: 'Cargando...',
  hostname: null,
  mac_address: null,
  operating_system: null,
  asset_type: 'server',
  criticality: 'medium',
  status: 'inactive',
  risk_score: 0,
  is_reachable: false,
  tags: [],
  description: undefined,
  last_seen_at: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export default function AssetDetailPage({ params }: AssetDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { data: asset, isLoading: assetLoading } = useAsset(id);
  const { data: services } = useAssetServices(id);
  const { data: vulnerabilities } = useAssetVulnerabilities(id);
  const deleteAsset = useDeleteAsset();
  const { toast } = useToast();
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Use API data with empty defaults
  const displayAsset = asset || emptyAsset;
  const displayServices = services || [];
  const displayVulns = vulnerabilities || [];

  const handleDeleteAsset = async () => {
    try {
      await deleteAsset.mutateAsync(id);
      toast({
        title: 'Asset eliminado',
        description: 'El asset ha sido eliminado correctamente.',
      });
      router.push('/assets');
    } catch (error) {
      toast({
        title: 'Error',
        description: 'No se pudo eliminar el asset.',
        variant: 'destructive',
      });
    }
  };

  if (assetLoading) {
    return (
      <div className="space-y-6">
        <div className="h-10 w-48 bg-muted animate-pulse rounded" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 bg-muted animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  const getRiskScoreVariant = (score: number) => {
    if (score >= 70) return 'danger';
    if (score >= 40) return 'warning';
    return 'success';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <Button
          variant="ghost"
          size="sm"
          className="w-fit"
          onClick={() => router.back()}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver
        </Button>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold font-mono">{displayAsset.ip_address}</h1>
              <StatusBadge status={displayAsset.status} size="lg" />
            </div>
            {displayAsset.hostname && (
              <p className="text-muted-foreground">{displayAsset.hostname}</p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline">
              <Pencil className="mr-2 h-4 w-4" />
              Editar
            </Button>
            <Button
              variant="destructive"
              onClick={() => setShowDeleteDialog(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Eliminar
            </Button>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Risk Score"
          value={displayAsset.risk_score}
          icon={Shield}
          variant={getRiskScoreVariant(displayAsset.risk_score)}
        />
        <StatCard
          title="Servicios"
          value={displayServices.length}
          description={`${displayServices.filter(s => s.state === 'open').length} abiertos`}
          icon={Network}
          variant="info"
        />
        <StatCard
          title="Vulnerabilidades"
          value={displayVulns.length}
          description={`${displayVulns.filter(v => v.severity === 'critical').length} críticas`}
          icon={AlertTriangle}
          variant={displayVulns.filter(v => v.severity === 'critical').length > 0 ? 'danger' : 'warning'}
        />
        <StatCard
          title="Último escaneo"
          value={
            displayAsset.last_seen_at
              ? formatDistanceToNow(new Date(displayAsset.last_seen_at), { locale: es })
              : '-'
          }
          icon={Radar}
          variant="default"
        />
      </div>

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>Información del Asset</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <div>
              <p className="text-sm text-muted-foreground">Sistema Operativo</p>
              <p className="font-medium">{displayAsset.operating_system || '-'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">MAC Address</p>
              <p className="font-mono">{displayAsset.mac_address || '-'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Tipo</p>
              <p className="font-medium capitalize">{displayAsset.asset_type.replace('_', ' ')}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Criticidad</p>
              <CriticalityBadge criticality={displayAsset.criticality} />
            </div>
          </div>
          {displayAsset.tags && displayAsset.tags.length > 0 && (
            <div className="mt-4 pt-4 border-t">
              <p className="text-sm text-muted-foreground mb-2">Tags</p>
              <div className="flex flex-wrap gap-2">
                {displayAsset.tags.map((tag) => (
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          {displayAsset.description && (
            <div className="mt-4 pt-4 border-t">
              <p className="text-sm text-muted-foreground mb-1">Descripción</p>
              <p>{displayAsset.description}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="services" className="space-y-4">
        <TabsList>
          <TabsTrigger value="services">Servicios</TabsTrigger>
          <TabsTrigger value="vulnerabilities">Vulnerabilidades</TabsTrigger>
          <TabsTrigger value="scans">Historial de Scans</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
        </TabsList>

        {/* Services Tab */}
        <TabsContent value="services">
          <Card>
            <CardHeader>
              <CardTitle>Servicios Detectados</CardTitle>
              <CardDescription>
                {displayServices.length} servicios encontrados
              </CardDescription>
            </CardHeader>
            <CardContent>
              {displayServices.length === 0 ? (
                <EmptyState
                  icon={Network}
                  title="Sin servicios"
                  description="No se han detectado servicios en este asset."
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Puerto</TableHead>
                      <TableHead>Protocolo</TableHead>
                      <TableHead>Servicio</TableHead>
                      <TableHead>Versión</TableHead>
                      <TableHead>Estado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {displayServices.map((service) => (
                      <TableRow key={service.id}>
                        <TableCell className="font-mono font-medium">{service.port}</TableCell>
                        <TableCell className="uppercase text-muted-foreground">{service.protocol}</TableCell>
                        <TableCell>{service.service_name}</TableCell>
                        <TableCell className="text-muted-foreground">{service.version || '-'}</TableCell>
                        <TableCell>
                          <span
                            className={`inline-flex items-center gap-1.5 text-xs font-medium ${
                              service.state === 'open'
                                ? 'text-status-success'
                                : service.state === 'filtered'
                                ? 'text-status-warning'
                                : 'text-muted-foreground'
                            }`}
                          >
                            <span
                              className={`h-1.5 w-1.5 rounded-full ${
                                service.state === 'open'
                                  ? 'bg-status-success'
                                  : service.state === 'filtered'
                                  ? 'bg-status-warning'
                                  : 'bg-muted-foreground'
                              }`}
                            />
                            {service.state === 'open' ? 'Abierto' : service.state === 'filtered' ? 'Filtrado' : 'Cerrado'}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Vulnerabilities Tab */}
        <TabsContent value="vulnerabilities">
          <Card>
            <CardHeader>
              <CardTitle>Vulnerabilidades</CardTitle>
              <CardDescription>
                {displayVulns.length} vulnerabilidades en este asset
              </CardDescription>
            </CardHeader>
            <CardContent>
              {displayVulns.length === 0 ? (
                <EmptyState
                  icon={AlertTriangle}
                  title="Sin vulnerabilidades"
                  description="No se han detectado vulnerabilidades en este asset."
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nombre</TableHead>
                      <TableHead>Severidad</TableHead>
                      <TableHead>CVE</TableHead>
                      <TableHead>CVSS</TableHead>
                      <TableHead>Estado</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {displayVulns.map((vuln) => (
                      <TableRow key={vuln.id}>
                        <TableCell>
                          <Link
                            href={`/vulnerabilities/${vuln.id}`}
                            className="font-medium hover:text-primary transition-colors"
                          >
                            {vuln.name}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <SeverityBadge severity={vuln.severity} size="sm" />
                        </TableCell>
                        <TableCell>
                          {vuln.cve_id ? (
                            <code className="text-sm">{vuln.cve_id}</code>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-sm font-medium">
                            {vuln.cvss_score?.toFixed(1) || '-'}
                          </span>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={vuln.status} size="sm" />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Scans Tab */}
        <TabsContent value="scans">
          <Card>
            <CardHeader>
              <CardTitle>Historial de Escaneos</CardTitle>
              <CardDescription>
                Escaneos que incluyeron este asset
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EmptyState
                icon={Radar}
                title="Sin escaneos"
                description="Este asset no ha sido incluido en ningún escaneo aún. El historial de escaneos estará disponible próximamente."
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Timeline Tab */}
        <TabsContent value="timeline">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Timeline
              </CardTitle>
              <CardDescription>
                Historial de cambios y eventos
              </CardDescription>
            </CardHeader>
            <CardContent>
              <EmptyState
                icon={Activity}
                title="Sin eventos"
                description="El timeline de eventos para este asset estará disponible próximamente."
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Delete Dialog */}
      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Eliminar asset"
        description="¿Estás seguro de que deseas eliminar este asset? Esta acción eliminará también todas las vulnerabilidades y datos asociados."
        confirmLabel="Eliminar"
        variant="destructive"
        onConfirm={handleDeleteAsset}
      />
    </div>
  );
}
