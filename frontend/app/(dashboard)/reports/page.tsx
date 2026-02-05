"use client";

import { useState } from "react";
import {
  FileText,
  Download,
  Calendar,
  Filter,
  Clock,
  CheckCircle2,
  AlertTriangle,
  BarChart3,
  PieChart,
  FileJson,
  FileSpreadsheet,
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
import { PageHeader } from "@/components/shared/page-header";
import { EmptyState } from "@/components/shared/empty-state";
import { formatDistanceToNow, format } from "date-fns";
import { es } from "date-fns/locale";

// Report types available
const reportTypes = [
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
    id: "compliance",
    name: "Reporte de Cumplimiento",
    description: "Estado de cumplimiento normativo",
    icon: CheckCircle2,
    color: "text-green-500",
  },
  {
    id: "vulnerability",
    name: "Reporte de Vulnerabilidades",
    description: "Lista detallada de todas las vulnerabilidades",
    icon: AlertTriangle,
    color: "text-red-500",
  },
];

const formatIcons: Record<string, React.ReactNode> = {
  pdf: <FileText className="h-4 w-4 text-red-500" />,
  json: <FileJson className="h-4 w-4 text-yellow-500" />,
  xlsx: <FileSpreadsheet className="h-4 w-4 text-green-500" />,
};

export default function ReportsPage() {
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<string>("pdf");
  const [dateRange, setDateRange] = useState<string>("30d");
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerateReport = async () => {
    if (!selectedType) return;
    
    setIsGenerating(true);
    // Simular generación de reporte
    await new Promise((resolve) => setTimeout(resolve, 2000));
    setIsGenerating(false);
    
    // En producción, esto llamaría a la API
    alert(`Reporte de tipo "${selectedType}" generado en formato ${selectedFormat.toUpperCase()}`);
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Reportes"
        description="Genera y descarga reportes de seguridad"
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
            {reportTypes.map((type) => {
              const Icon = type.icon;
              const isSelected = selectedType === type.id;
              return (
                <button
                  key={type.id}
                  onClick={() => setSelectedType(type.id)}
                  className={`flex flex-col items-start p-4 rounded-lg border-2 transition-all ${
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
            <div className="space-y-2">
              <label className="text-sm font-medium">Formato</label>
              <Select value={selectedFormat} onValueChange={setSelectedFormat}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="xlsx">Excel</SelectItem>
                  <SelectItem value="json">JSON</SelectItem>
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
              disabled={!selectedType || isGenerating}
              className="ml-auto"
            >
              {isGenerating ? (
                <>
                  <Clock className="h-4 w-4 mr-2 animate-spin" />
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
          <EmptyState
            icon={FileText}
            title="Sin reportes"
            description="Aún no has generado ningún reporte. Usa el formulario de arriba para crear uno."
          />
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
                <p className="text-2xl font-bold">0</p>
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
                <p className="text-2xl font-bold">0</p>
                <p className="text-sm text-muted-foreground">Reportes de Cumplimiento</p>
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
                <p className="text-2xl font-bold">0</p>
                <p className="text-sm text-muted-foreground">Reportes Ejecutivos</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
