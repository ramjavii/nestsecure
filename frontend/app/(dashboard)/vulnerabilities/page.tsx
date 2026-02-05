"use client";

import React from "react"

import { useState, useMemo, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  Shield,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  AlertTriangle,
  Clock,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { SeverityBadge } from "@/components/shared/severity-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { TableSkeleton } from "@/components/shared/loading-skeleton";
import { useVulnerabilities } from "@/hooks/use-vulnerabilities";
import type { Vulnerability, VulnerabilityStatus, Severity } from "@/types";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";

const statusConfig: Record<
  VulnerabilityStatus,
  { label: string; icon: React.ReactNode; className: string }
> = {
  open: {
    label: "Abierta",
    icon: <AlertTriangle className="h-3 w-3" />,
    className: "bg-red-500/20 text-red-400 border-red-500/30",
  },
  in_progress: {
    label: "En Progreso",
    icon: <Clock className="h-3 w-3" />,
    className: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  },
  resolved: {
    label: "Resuelta",
    icon: <CheckCircle2 className="h-3 w-3" />,
    className: "bg-green-500/20 text-green-400 border-green-500/30",
  },
  false_positive: {
    label: "Falso Positivo",
    icon: <XCircle className="h-3 w-3" />,
    className: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  },
  accepted: {
    label: "Aceptada",
    icon: <CheckCircle2 className="h-3 w-3" />,
    className: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  },
};

function VulnerabilitiesPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [severity, setSeverity] = useState<Severity | "all">(
    (searchParams.get("severity") as Severity) || "all"
  );
  const [status, setStatus] = useState<VulnerabilityStatus | "all">(
    (searchParams.get("status") as VulnerabilityStatus) || "all"
  );
  const [page, setPage] = useState(Number(searchParams.get("page")) || 1);

  const filters = useMemo(
    () => ({
      search: search || undefined,
      severity: severity !== "all" ? severity : undefined,
      status: status !== "all" ? status : undefined,
      page,
      limit: 10,
    }),
    [search, severity, status, page]
  );

  const { vulnerabilities, isLoading, error, pagination } =
    useVulnerabilities(filters);

  const handleRowClick = (vuln: Vulnerability) => {
    router.push(`/vulnerabilities/${vuln.id}`);
  };

  const handleSearch = (value: string) => {
    setSearch(value);
    setPage(1);
  };

  const handleSeverityChange = (value: string) => {
    setSeverity(value as Severity | "all");
    setPage(1);
  };

  const handleStatusChange = (value: string) => {
    setStatus(value as VulnerabilityStatus | "all");
    setPage(1);
  };

  // Summary stats
  const stats = useMemo(() => {
    if (!vulnerabilities.length) return null;
    return {
      critical: vulnerabilities.filter((v: Vulnerability) => v.severity === "critical").length,
      high: vulnerabilities.filter((v: Vulnerability) => v.severity === "high").length,
      medium: vulnerabilities.filter((v: Vulnerability) => v.severity === "medium").length,
      low: vulnerabilities.filter((v: Vulnerability) => v.severity === "low").length,
    };
  }, [vulnerabilities]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Vulnerabilidades"
        description="Gestiona y monitorea las vulnerabilidades detectadas"
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">
                  Críticas
                </p>
                <p className="text-2xl font-bold text-red-500">
                  {stats?.critical || 0}
                </p>
              </div>
              <div className="h-10 w-10 rounded-lg bg-red-500/10 flex items-center justify-center">
                <AlertTriangle className="h-5 w-5 text-red-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">
                  Altas
                </p>
                <p className="text-2xl font-bold text-orange-500">
                  {stats?.high || 0}
                </p>
              </div>
              <div className="h-10 w-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
                <Shield className="h-5 w-5 text-orange-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">
                  Medias
                </p>
                <p className="text-2xl font-bold text-yellow-500">
                  {stats?.medium || 0}
                </p>
              </div>
              <div className="h-10 w-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
                <Shield className="h-5 w-5 text-yellow-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card border-border">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">
                  Bajas
                </p>
                <p className="text-2xl font-bold text-blue-500">
                  {stats?.low || 0}
                </p>
              </div>
              <div className="h-10 w-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <Shield className="h-5 w-5 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="bg-card border-border">
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Buscar por título, CVE o asset..."
                value={search}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-9 bg-secondary border-border"
              />
            </div>
            <div className="flex gap-3">
              <Select value={severity} onValueChange={handleSeverityChange}>
                <SelectTrigger className="w-[140px] bg-secondary border-border">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="Severidad" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas</SelectItem>
                  <SelectItem value="critical">Crítica</SelectItem>
                  <SelectItem value="high">Alta</SelectItem>
                  <SelectItem value="medium">Media</SelectItem>
                  <SelectItem value="low">Baja</SelectItem>
                  <SelectItem value="info">Info</SelectItem>
                </SelectContent>
              </Select>
              <Select value={status} onValueChange={handleStatusChange}>
                <SelectTrigger className="w-[160px] bg-secondary border-border">
                  <SelectValue placeholder="Estado" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="open">Abierta</SelectItem>
                  <SelectItem value="in_progress">En Progreso</SelectItem>
                  <SelectItem value="resolved">Resuelta</SelectItem>
                  <SelectItem value="false_positive">Falso Positivo</SelectItem>
                  <SelectItem value="accepted">Aceptada</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-0">
          <CardTitle className="text-lg font-semibold">
            Lista de Vulnerabilidades
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4">
              <TableSkeleton rows={10} columns={6} />
            </div>
          ) : error ? (
            <div className="p-8 text-center text-destructive">
              Error al cargar vulnerabilidades
            </div>
          ) : vulnerabilities.length === 0 ? (
            <EmptyState
              icon={Shield}
              title="No hay vulnerabilidades"
              description="No se encontraron vulnerabilidades con los filtros aplicados"
            />
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border hover:bg-transparent">
                      <TableHead className="text-muted-foreground">
                        Severidad
                      </TableHead>
                      <TableHead className="text-muted-foreground">
                        Título
                      </TableHead>
                      <TableHead className="text-muted-foreground">
                        CVE
                      </TableHead>
                      <TableHead className="text-muted-foreground">
                        Asset
                      </TableHead>
                      <TableHead className="text-muted-foreground">
                        Estado
                      </TableHead>
                      <TableHead className="text-muted-foreground">
                        Detectada
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {vulnerabilities.map((vuln: Vulnerability) => (
                      <TableRow
                        key={vuln.id}
                        className="border-border cursor-pointer hover:bg-accent/50 transition-colors"
                        onClick={() => handleRowClick(vuln)}
                      >
                        <TableCell>
                          <SeverityBadge severity={vuln.severity} />
                        </TableCell>
                        <TableCell>
                          <div className="max-w-[300px]">
                            <p className="font-medium text-foreground truncate">
                              {vuln.name}
                            </p>
                            <p className="text-xs text-muted-foreground truncate">
                              CVSS: {vuln.cvss_score?.toFixed(1) || "N/A"}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          {vuln.cve_id ? (
                            <Badge
                              variant="outline"
                              className="font-mono text-xs bg-secondary/50"
                            >
                              {vuln.cve_id}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground text-sm">
                              —
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-foreground">
                              {vuln.asset?.hostname || vuln.asset?.ip_address || "—"}
                            </span>
                            {vuln.asset && (
                              <ExternalLink className="h-3 w-3 text-muted-foreground" />
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {statusConfig[vuln.status as VulnerabilityStatus] && (
                            <Badge
                              variant="outline"
                              className={`${statusConfig[vuln.status as VulnerabilityStatus].className} gap-1`}
                            >
                              {statusConfig[vuln.status as VulnerabilityStatus].icon}
                              {statusConfig[vuln.status as VulnerabilityStatus].label}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {formatDistanceToNow(new Date(vuln.detected_at), {
                            addSuffix: true,
                            locale: es,
                          })}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {pagination && pagination.pages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-border">
                  <p className="text-sm text-muted-foreground">
                    Mostrando {(page - 1) * 10 + 1} -{" "}
                    {Math.min(page * 10, pagination.total)} de{" "}
                    {pagination.total}
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page - 1)}
                      disabled={page === 1}
                      className="bg-transparent"
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      Página {page} de {pagination.pages}
                    </span>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(page + 1)}
                      disabled={page >= pagination.pages}
                      className="bg-transparent"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function VulnerabilitiesPage() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col gap-6">
          <PageHeader
            title="Vulnerabilidades"
            description="Gestiona y monitorea las vulnerabilidades detectadas"
          />
          <TableSkeleton rows={10} columns={6} />
        </div>
      }
    >
      <VulnerabilitiesPageContent />
    </Suspense>
  );
}
