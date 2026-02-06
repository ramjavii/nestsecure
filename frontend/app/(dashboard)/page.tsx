'use client';

import { Server, Radar, AlertTriangle, Shield } from 'lucide-react';
import { StatCard } from '@/components/shared/stat-card';
import { VulnTrendChart } from '@/components/dashboard/vuln-trend-chart';
import { SeverityPieChart } from '@/components/dashboard/severity-pie-chart';
import { RecentScansTable } from '@/components/dashboard/recent-scans-table';
import { TopVulnsTable } from '@/components/dashboard/top-vulns-table';
import { PageHeader } from '@/components/shared/page-header';
import { useDashboardStats, useRecentScans, useVulnerabilityTrend, useTopVulnerabilities } from '@/hooks/use-dashboard';

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: recentScans, isLoading: scansLoading } = useRecentScans();
  const { data: vulnTrend, isLoading: trendLoading } = useVulnerabilityTrend();
  const { data: topVulns, isLoading: vulnsLoading } = useTopVulnerabilities(5);

  // Default empty stats when no data from API
  const emptyStats = {
    assets: { total: 0, active: 0, inactive: 0 },
    scans: { running: 0, completed: 0 },
    vulnerabilities: { 
      total: 0, 
      critical: 0, 
      high: 0, 
      medium: 0, 
      low: 0, 
      info: 0,
      open: 0,
      fixed: 0 
    },
    risk_score: 0,
  };

  const displayStats = stats || emptyStats;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Resumen general de seguridad de tu infraestructura"
      />

      {/* Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Assets"
          value={displayStats.assets?.total || 0}
          description={`${displayStats.assets?.active || 0} activos`}
          icon={Server}
          variant="info"
          isLoading={statsLoading}
        />
        <StatCard
          title="Escaneos Activos"
          value={displayStats.scans?.running || 0}
          description={`${displayStats.scans?.completed || 0} completados`}
          icon={Radar}
          variant="default"
          isLoading={statsLoading}
        />
        <StatCard
          title="Vulnerabilidades"
          value={displayStats.vulnerabilities?.total || 0}
          description={`${displayStats.vulnerabilities?.critical || 0} críticas`}
          icon={AlertTriangle}
          variant="danger"
          isLoading={statsLoading}
        />
        <StatCard
          title="Risk Score"
          value={displayStats.risk_score || 0}
          description="Puntuación de riesgo"
          icon={Shield}
          variant={
            (displayStats.risk_score || 0) >= 80
              ? 'danger'
              : (displayStats.risk_score || 0) >= 50
              ? 'warning'
              : 'success'
          }
          isLoading={statsLoading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <VulnTrendChart
          data={vulnTrend}
          isLoading={trendLoading}
        />
        <SeverityPieChart
          data={displayStats.vulnerabilities}
          isLoading={statsLoading}
        />
      </div>

      {/* Tables Row */}
      <div className="grid gap-6 xl:grid-cols-2">
        <RecentScansTable scans={recentScans} isLoading={scansLoading} />
        <TopVulnsTable vulnerabilities={topVulns} isLoading={vulnsLoading} />
      </div>
    </div>
  );
}
