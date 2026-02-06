'use client';

import Link from 'next/link';
import { ExternalLink, AlertTriangle } from 'lucide-react';
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
import { SeverityBadge } from '@/components/shared/severity-badge';
import { StatusBadge } from '@/components/shared/status-badge';
import { TableSkeleton } from '@/components/shared/loading-skeleton';
import { EmptyState } from '@/components/shared/empty-state';
import type { Vulnerability } from '@/types';

interface TopVulnsTableProps {
  vulnerabilities?: Vulnerability[];
  isLoading?: boolean;
}

export function TopVulnsTable({ vulnerabilities, isLoading }: TopVulnsTableProps) {
  // Use real data only - no mock fallback
  const data: Vulnerability[] = vulnerabilities || [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Top Vulnerabilidades</CardTitle>
          <CardDescription>Vulnerabilidades prioritarias por severidad</CardDescription>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link href="/vulnerabilities">
            Ver todas
            <ExternalLink className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <TableSkeleton rows={5} columns={5} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={AlertTriangle}
            title="No hay vulnerabilidades"
            description="No se han detectado vulnerabilidades."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Vulnerabilidad</TableHead>
                <TableHead>Severidad</TableHead>
                <TableHead>CVE</TableHead>
                <TableHead>CVSS</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((vuln) => (
                <TableRow key={vuln.id}>
                  <TableCell>
                    <Link
                      href={`/vulnerabilities/${vuln.id}`}
                      className="font-medium hover:text-primary transition-colors line-clamp-1 max-w-xs"
                    >
                      {vuln.name}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <SeverityBadge severity={vuln.severity} size="sm" />
                  </TableCell>
                  <TableCell>
                    {vuln.cve_id ? (
                      <a
                        href={`https://nvd.nist.gov/vuln/detail/${vuln.cve_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-primary hover:underline font-mono"
                      >
                        {vuln.cve_id}
                      </a>
                    ) : (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <span
                      className={`font-mono text-sm font-medium ${
                        (vuln.cvss_score || 0) >= 9
                          ? 'text-severity-critical'
                          : (vuln.cvss_score || 0) >= 7
                          ? 'text-severity-high'
                          : (vuln.cvss_score || 0) >= 4
                          ? 'text-severity-medium'
                          : 'text-severity-low'
                      }`}
                    >
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
  );
}
