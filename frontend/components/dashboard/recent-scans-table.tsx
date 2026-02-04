'use client';

import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { es } from 'date-fns/locale';
import { ExternalLink } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { StatusBadge } from '@/components/shared/status-badge';
import { ProgressBar } from '@/components/shared/progress-bar';
import { TableSkeleton } from '@/components/shared/loading-skeleton';
import { EmptyState } from '@/components/shared/empty-state';
import type { Scan } from '@/types';
import { Radar } from 'lucide-react';

interface RecentScansTableProps {
  scans?: Scan[];
  isLoading?: boolean;
}

const scanTypeLabels: Record<string, string> = {
  discovery: 'Descubrimiento',
  port_scan: 'Escaneo de Puertos',
  service_scan: 'Detección de Servicios',
  vulnerability: 'Vulnerabilidades',
  full: 'Completo',
};

export function RecentScansTable({ scans, isLoading }: RecentScansTableProps) {
  // Mock data for demo
  const data: Scan[] = scans || [
    {
      id: '1',
      name: 'Escaneo Red Interna',
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
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Últimos Escaneos</CardTitle>
          <CardDescription>Actividad reciente de escaneos</CardDescription>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link href="/scans">
            Ver todos
            <ExternalLink className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <TableSkeleton rows={4} columns={5} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={Radar}
            title="No hay escaneos"
            description="No se han realizado escaneos recientemente."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nombre</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Progreso</TableHead>
                <TableHead className="text-right">Fecha</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((scan) => (
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
                    {scanTypeLabels[scan.scan_type] || scan.scan_type}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={scan.status} size="sm" />
                  </TableCell>
                  <TableCell className="w-32">
                    <ProgressBar
                      value={scan.progress}
                      size="sm"
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
                  <TableCell className="text-right text-sm text-muted-foreground">
                    {formatDistanceToNow(new Date(scan.created_at), {
                      addSuffix: true,
                      locale: es,
                    })}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
