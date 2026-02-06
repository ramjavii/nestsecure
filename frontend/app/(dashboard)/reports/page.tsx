"use client";

import { useState, useMemo } from "react";
import {
  FileText,
  Download,
  Clock,
  CheckCircle2,
  AlertTriangle,
  BarChart3,
  PieChart,
  FileJson,
  FileSpreadsheet,
  Trash2,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { LoadingSpinner } from "@/components/shared/loading-spinner";
import { formatDistanceToNow, format, subDays } from "date-fns";
import { es } from "date-fns/locale";
import {
  useReports,
  useGenerateReport,
  useDownloadReport,
  useDeleteReport,
  REPORT_TYPES,
  REPORT_FORMATS,
  REPORT_STATUSES,
} from "@/hooks/use-reports";
import type { ReportType, ReportFormat, ReportStatus } from "@/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

// Report types available
const reportTypeConfigs = [
  {
    id: "executive",
    name: "Reporte Ejecutivo",
    description: "Resumen de alto nivel para stakeholders",
    icon: BarChart3,
    color: "text-blue-500",
  },
  {
    id: "technical",
    name: "Reporte Técnico",
    description: "Detalles completos de vulnerabilidades y remediación",
    icon: FileText,
    color: "text-purple-500",
  },
  {
    id: "vulnerability",
    name: "Reporte de Vulnerabilidades",
    description: "Lista detallada de todas las vulnerabilidades",
    icon: AlertTriangle,
    color: "text-red-500",
  },
  {
    id: "asset_inventory",
    name: "Inventario de Assets",
    description: "Lista completa de activos de la organización",
    icon: PieChart,
    color: "text-green-500",
  },
];

const formatIcons: Record<string, React.ReactNode> = {
  pdf: <FileText className="h-4 w-4 text-red-500" />,
  json: <FileJson className="h-4 w-4 text-yellow-500" />,
  xlsx: <FileSpreadsheet className="h-4 w-4 text-green-500" />,
  csv: <FileSpreadsheet className="h-4 w-4 text-blue-500" />,
};

const statusBadgeVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  pending: "secondary",
  generating: "default",
  completed: "outline",
  failed: "destructive",
};

export default function ReportsPage() {
  const [selectedType, setSelectedType] = useState<ReportType | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<ReportFormat>("pdf");
  const [dateRange, setDateRange] = useState<string>("30d");
  const [reportName, setReportName] = useState("");

  // API hooks
  const { data: reportsData, isLoading, refetch } = useReports({ page: 1, page_size: 50 });
  const generateMutation = useGenerateReport();
  const downloadMutation = useDownloadReport();
  const deleteMutation = useDeleteReport();

  const reports = reportsData?.reports ?? [];

  // Stats
  const stats = useMemo(() => {
    const total = reports.length;
    const completed = reports.filter((r) => r.status === "completed").length;
    const executive = reports.filter((r) => r.report_type === "executive").length;
    return { total, completed, executive };
  }, [reports]);

  const handleGenerateReport = () => {
    if (!selectedType) return;

    // Calculate date range
    let dateFrom: string | undefined;
    const now = new Date();
    
    switch (dateRange) {
      case "7d":
        dateFrom = subDays(now, 7).toISOString();
        break;
      case "30d":
        dateFrom = subDays(now, 30).toISOString();
        break;
      case "90d":
        dateFrom = subDays(now, 90).toISOString();
        break;
      default:
        dateFrom = undefined;
    }

    const name = reportName || `Reporte ${selectedType} - ${format(now, "dd/MM/yyyy HH:mm")}`;

    generateMutation.mutate({
      name,
      report_type: selectedType,
      format: selectedFormat,
      date_from: dateFrom,
    });

    // Reset form
    setReportName("");
    setSelectedType(null);
  };

  const handleDownload = (report: { id: string; name: string; format: string }) => {
    downloadMutation.mutate(report);
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reportes"
        description="Genera y descarga reportes de seguridad"
        actions={
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualizar
          </Button>
        }
      />

      {/* Report Generator */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Generar Nuevo Reporte
          </CardTitle>
          <CardDescription>
            Selecciona el tipo de reporte que deseas generar
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Report Type Selection */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
            {reportTypeConfigs.map((type) => {
              const Icon = type.icon;
              const isSelected = selectedType === type.id;
              return (
                <button
                  key={type.id}
                  onClick={() => setSelectedType(type.id as ReportType)}
                  className={`flex flex-col items-start p-4 rounded-lg border-2 transition-all text-left ${
                    isSelected
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-muted-foreground/50"
                  }`}
                >
                  <Icon className={`h-8 w-8 mb-2 ${type.color}`} />
                  <span className="font-medium">{type.name}</span>
                  <span className="text-xs text-muted-foreground mt-1">
                    {type.description}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Options */}
          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-2 flex-1 min-w-[200px]">
              <label className="text-sm font-medium">Nombre del Reporte</label>
              <Input
                placeholder="Nombre personalizado (opcional)"
                value={reportName}
                onChange={(e) => setReportName(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Formato</label>
              <Select value={selectedFormat} onValueChange={(v) => setSelectedFormat(v as ReportFormat)}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {REPORT_FORMATS.map((f) => (
                    <SelectItem key={f.value} value={f.value}>
                      {f.icon} {f.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Período</label>
              <Select value={dateRange} onValueChange={setDateRange}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7d">Últimos 7 días</SelectItem>
                  <SelectItem value="30d">Últimos 30 días</SelectItem>
                  <SelectItem value="90d">Últimos 90 días</SelectItem>
                  <SelectItem value="all">Todo el historial</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button
              onClick={handleGenerateReport}
              disabled={!selectedType || generateMutation.isPending}
              className="ml-auto"
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generando...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4 mr-2" />
                  Generar Reporte
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recent Reports */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Reportes Recientes
          </CardTitle>
          <CardDescription>
            Reportes generados anteriormente disponibles para descarga
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <LoadingSpinner />
          ) : reports.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="Sin reportes"
              description="Aún no has generado ningún reporte. Usa el formulario de arriba para crear uno."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nombre</TableHead>
                  <TableHead>Tipo</TableHead>
                  <TableHead>Formato</TableHead>
                  <TableHead>Estado</TableHead>
                  <TableHead>Fecha</TableHead>
                  <TableHead className="text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {reports.map((report) => (
                  <TableRow key={report.id}>
                    <TableCell className="font-medium">{report.name}</TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {REPORT_TYPES.find((t) => t.value === report.report_type)?.label || report.report_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {formatIcons[report.format]}
                        <span className="uppercase text-xs">{report.format}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusBadgeVariants[report.status] || "secondary"}>
                        {report.status === "generating" && (
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        )}
                        {REPORT_STATUSES[report.status as ReportStatus]?.label || report.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {formatDistanceToNow(new Date(report.created_at), {
                        addSuffix: true,
                        locale: es,
                      })}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        {report.is_downloadable && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDownload({
                              id: report.id,
                              name: report.name,
                              format: report.format,
                            })}
                            disabled={downloadMutation.isPending}
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        )}
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-destructive hover:text-destructive"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>¿Eliminar reporte?</AlertDialogTitle>
                              <AlertDialogDescription>
                                Esta acción no se puede deshacer. El reporte &quot;{report.name}&quot; será eliminado permanentemente.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancelar</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => handleDelete(report.id)}
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              >
                                Eliminar
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-blue-500/10">
                <FileText className="h-6 w-6 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.total}</p>
                <p className="text-sm text-muted-foreground">Reportes Generados</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-green-500/10">
                <CheckCircle2 className="h-6 w-6 text-green-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.completed}</p>
                <p className="text-sm text-muted-foreground">Reportes Completados</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-purple-500/10">
                <PieChart className="h-6 w-6 text-purple-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.executive}</p>
                <p className="text-sm text-muted-foreground">Reportes Ejecutivos</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
