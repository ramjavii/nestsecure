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
  // Mock data for demo
  const data: Vulnerability[] = vulnerabilities || [
    {
      id: '1',
      name: 'Remote Code Execution in Apache Log4j',
      description: 'Critical vulnerability allowing remote code execution',
      severity: 'critical',
      status: 'open',
      cve_id: 'CVE-2021-44228',
      cvss_score: 10.0,
      cvss_vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H',
      cwe_id: 'CWE-502',
      asset_id: 'asset-1',
      solution: 'Update Log4j to version 2.17.0 or later',
      references: ['https://nvd.nist.gov/vuln/detail/CVE-2021-44228'],
      exploit_available: true,
      detected_at: new Date(Date.now() - 86400000).toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: '2',
      name: 'SQL Injection in Login Form',
      description: 'SQL injection vulnerability in authentication endpoint',
      severity: 'critical',
      status: 'in_progress',
      cve_id: null,
      cvss_score: 9.8,
      cvss_vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
      cwe_id: 'CWE-89',
      asset_id: 'asset-2',
      solution: 'Use parameterized queries or prepared statements',
      references: [],
      exploit_available: true,
      detected_at: new Date(Date.now() - 172800000).toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: '3',
      name: 'OpenSSL Buffer Overflow',
      description: 'Buffer overflow in OpenSSL TLS implementation',
      severity: 'high',
      status: 'open',
      cve_id: 'CVE-2022-3602',
      cvss_score: 7.5,
      cvss_vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H',
      cwe_id: 'CWE-120',
      asset_id: 'asset-3',
      solution: 'Update OpenSSL to version 3.0.7 or later',
      references: ['https://nvd.nist.gov/vuln/detail/CVE-2022-3602'],
      exploit_available: false,
      detected_at: new Date(Date.now() - 259200000).toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: '4',
      name: 'Cross-Site Scripting (XSS)',
      description: 'Reflected XSS vulnerability in search functionality',
      severity: 'medium',
      status: 'accepted',
      cve_id: null,
      cvss_score: 6.1,
      cvss_vector: 'CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N',
      cwe_id: 'CWE-79',
      asset_id: 'asset-4',
      solution: 'Implement proper input sanitization and output encoding',
      references: [],
      exploit_available: false,
      detected_at: new Date(Date.now() - 345600000).toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: '5',
      name: 'Weak SSH Encryption',
      description: 'SSH server using deprecated encryption algorithms',
      severity: 'low',
      status: 'resolved',
      cve_id: null,
      cvss_score: 3.7,
      cvss_vector: 'CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N',
      cwe_id: 'CWE-327',
      asset_id: 'asset-5',
      solution: 'Disable weak ciphers in SSH configuration',
      references: [],
      exploit_available: false,
      detected_at: new Date(Date.now() - 432000000).toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

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
