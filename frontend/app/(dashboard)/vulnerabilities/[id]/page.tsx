"use client";

import React from "react"

import { useState, use } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Shield,
  ExternalLink,
  Clock,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  FileText,
  Server,
  Activity,
  Link as LinkIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { PageHeader } from "@/components/shared/page-header";
import { SeverityBadge } from "@/components/shared/severity-badge";
import { CardSkeleton } from "@/components/shared/loading-skeleton";
import { useVulnerability, useUpdateVulnerabilityStatus } from "@/hooks/use-vulnerabilities";
import { useToast } from "@/hooks/use-toast";
import type { VulnerabilityStatus } from "@/types";
import { format } from "date-fns";
import { es } from "date-fns/locale";

const statusConfig: Record<
  VulnerabilityStatus,
  { label: string; icon: React.ReactNode; className: string }
> = {
  open: {
    label: "Abierta",
    icon: <AlertTriangle className="h-4 w-4" />,
    className: "bg-red-500/20 text-red-400 border-red-500/30",
  },
  in_progress: {
    label: "En Progreso",
    icon: <Clock className="h-4 w-4" />,
    className: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  },
  resolved: {
    label: "Resuelta",
    icon: <CheckCircle2 className="h-4 w-4" />,
    className: "bg-green-500/20 text-green-400 border-green-500/30",
  },
  false_positive: {
    label: "Falso Positivo",
    icon: <XCircle className="h-4 w-4" />,
    className: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  },
  accepted: {
    label: "Aceptada",
    icon: <CheckCircle2 className="h-4 w-4" />,
    className: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  },
};

interface VulnerabilityDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function VulnerabilityDetailPage({
  params,
}: VulnerabilityDetailPageProps) {
  const { id } = use(params);
  const router = useRouter();
  const { toast } = useToast();
  const { vulnerability, isLoading, error, mutate } = useVulnerability(id);
  const { updateStatus, isUpdating } = useUpdateVulnerabilityStatus();
  const [notes, setNotes] = useState("");

  const handleStatusChange = async (newStatus: VulnerabilityStatus) => {
    try {
      await updateStatus(id, newStatus);
      mutate();
      toast({
        title: "Estado actualizado",
        description: `La vulnerabilidad ahora está ${statusConfig[newStatus].label.toLowerCase()}`,
      });
    } catch {
      toast({
        title: "Error",
        description: "No se pudo actualizar el estado",
        variant: "destructive",
      });
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.back()}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver
          </Button>
        </div>
        <CardSkeleton count={3} />
      </div>
    );
  }

  if (error || !vulnerability) {
    return (
      <div className="flex flex-col gap-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.back()}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver
          </Button>
        </div>
        <Card className="bg-card border-border">
          <CardContent className="p-8 text-center">
            <Shield className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              Vulnerabilidad no encontrada
            </h3>
            <p className="text-muted-foreground">
              La vulnerabilidad solicitada no existe o no tienes acceso.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.back()}
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Volver
          </Button>
        </div>
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
              <Shield className="h-6 w-6 text-primary" />
            </div>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-xl font-bold text-foreground">
                  {vulnerability.title}
                </h1>
                <SeverityBadge severity={vulnerability.severity} size="lg" />
              </div>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                {vulnerability.cve_id && (
                  <Badge
                    variant="outline"
                    className="font-mono bg-secondary/50"
                  >
                    {vulnerability.cve_id}
                  </Badge>
                )}
                <span>CVSS: {vulnerability.cvss_score?.toFixed(1) || "N/A"}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Select
              value={vulnerability.status}
              onValueChange={handleStatusChange}
              disabled={isUpdating}
            >
              <SelectTrigger className="w-[180px] bg-secondary border-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="open">Abierta</SelectItem>
                <SelectItem value="in_progress">En Progreso</SelectItem>
                <SelectItem value="resolved">Resuelta</SelectItem>
                <SelectItem value="false_positive">Falso Positivo</SelectItem>
                <SelectItem value="accepted">Aceptada</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - Details */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <Tabs defaultValue="details" className="w-full">
            <TabsList className="bg-secondary border border-border">
              <TabsTrigger value="details">Detalles</TabsTrigger>
              <TabsTrigger value="remediation">Remediación</TabsTrigger>
              <TabsTrigger value="evidence">Evidencia</TabsTrigger>
              <TabsTrigger value="history">Historial</TabsTrigger>
            </TabsList>

            <TabsContent value="details" className="mt-4">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <FileText className="h-5 w-5 text-primary" />
                    Descripción
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground leading-relaxed">
                    {vulnerability.description || "Sin descripción disponible"}
                  </p>

                  {vulnerability.cwe_id && (
                    <div className="mt-6 pt-6 border-t border-border">
                      <h4 className="font-medium mb-2">CWE</h4>
                      <Badge
                        variant="outline"
                        className="font-mono bg-secondary/50"
                      >
                        {vulnerability.cwe_id}
                      </Badge>
                    </div>
                  )}

                  {vulnerability.references && vulnerability.references.length > 0 && (
                    <div className="mt-6 pt-6 border-t border-border">
                      <h4 className="font-medium mb-3 flex items-center gap-2">
                        <LinkIcon className="h-4 w-4" />
                        Referencias
                      </h4>
                      <ul className="space-y-2">
                        {vulnerability.references.map((ref, idx) => (
                          <li key={idx}>
                            <a
                              href={ref}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary hover:underline flex items-center gap-2 text-sm"
                            >
                              <ExternalLink className="h-3 w-3" />
                              {ref}
                            </a>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="remediation" className="mt-4">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    Solución Recomendada
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground leading-relaxed whitespace-pre-wrap">
                    {vulnerability.remediation || "Sin recomendaciones de remediación disponibles."}
                  </p>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="evidence" className="mt-4">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Activity className="h-5 w-5 text-primary" />
                    Evidencia Técnica
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {vulnerability.evidence ? (
                    <div className="bg-secondary/50 rounded-lg p-4 font-mono text-sm overflow-x-auto">
                      <pre className="whitespace-pre-wrap text-muted-foreground">
                        {vulnerability.evidence}
                      </pre>
                    </div>
                  ) : (
                    <p className="text-muted-foreground">
                      No hay evidencia técnica disponible.
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="history" className="mt-4">
              <Card className="bg-card border-border">
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Clock className="h-5 w-5 text-primary" />
                    Historial de Cambios
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="relative pl-6 border-l border-border space-y-6">
                    <div className="relative">
                      <div className="absolute -left-[25px] h-4 w-4 rounded-full bg-primary"></div>
                      <div>
                        <p className="font-medium text-foreground">
                          Vulnerabilidad detectada
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {format(
                            new Date(vulnerability.detected_at),
                            "d 'de' MMMM, yyyy 'a las' HH:mm",
                            { locale: es }
                          )}
                        </p>
                      </div>
                    </div>
                    {vulnerability.resolved_at && (
                      <div className="relative">
                        <div className="absolute -left-[25px] h-4 w-4 rounded-full bg-green-500"></div>
                        <div>
                          <p className="font-medium text-foreground">
                            Vulnerabilidad resuelta
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {format(
                              new Date(vulnerability.resolved_at),
                              "d 'de' MMMM, yyyy 'a las' HH:mm",
                              { locale: es }
                            )}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Notes */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-lg">Notas Internas</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                placeholder="Agregar notas sobre esta vulnerabilidad..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="min-h-[100px] bg-secondary border-border resize-none"
              />
              <Button size="sm">Guardar Notas</Button>
            </CardContent>
          </Card>
        </div>

        {/* Right Column - Info Cards */}
        <div className="flex flex-col gap-6">
          {/* Status Card */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                Estado Actual
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Badge
                variant="outline"
                className={`${statusConfig[vulnerability.status].className} gap-2 text-sm py-1.5 px-3`}
              >
                {statusConfig[vulnerability.status].icon}
                {statusConfig[vulnerability.status].label}
              </Badge>
            </CardContent>
          </Card>

          {/* CVSS Score */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                CVSS Score
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-4">
                <div className="h-16 w-16 rounded-full bg-gradient-to-br from-red-500 to-orange-500 flex items-center justify-center">
                  <span className="text-xl font-bold text-white">
                    {vulnerability.cvss_score?.toFixed(1) || "N/A"}
                  </span>
                </div>
                <div>
                  <p className="font-medium">
                    {vulnerability.cvss_score
                      ? vulnerability.cvss_score >= 9
                        ? "Crítico"
                        : vulnerability.cvss_score >= 7
                          ? "Alto"
                          : vulnerability.cvss_score >= 4
                            ? "Medio"
                            : "Bajo"
                      : "No disponible"}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {vulnerability.cvss_vector || "Vector no disponible"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Asset Info */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <Server className="h-4 w-4" />
                Asset Afectado
              </CardTitle>
            </CardHeader>
            <CardContent>
              {vulnerability.asset ? (
                <div className="space-y-3">
                  <div>
                    <p className="font-medium text-foreground">
                      {vulnerability.asset.name}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {vulnerability.asset.type}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full gap-2 bg-transparent"
                    onClick={() =>
                      router.push(`/assets/${vulnerability.asset?.id}`)
                    }
                  >
                    <ExternalLink className="h-4 w-4" />
                    Ver Asset
                  </Button>
                </div>
              ) : (
                <p className="text-muted-foreground">No hay asset asociado</p>
              )}
            </CardContent>
          </Card>

          {/* Scan Info */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                Scan de Origen
              </CardTitle>
            </CardHeader>
            <CardContent>
              {vulnerability.scan ? (
                <div className="space-y-3">
                  <div>
                    <p className="font-medium text-foreground">
                      {vulnerability.scan.name}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {format(
                        new Date(vulnerability.scan.created_at),
                        "d MMM yyyy",
                        { locale: es }
                      )}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full gap-2 bg-transparent"
                    onClick={() =>
                      router.push(`/scans/${vulnerability.scan?.id}`)
                    }
                  >
                    <ExternalLink className="h-4 w-4" />
                    Ver Scan
                  </Button>
                </div>
              ) : (
                <p className="text-muted-foreground">No hay scan asociado</p>
              )}
            </CardContent>
          </Card>

          {/* Dates */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                Fechas
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground text-sm">Detectada</span>
                <span className="text-sm font-medium">
                  {format(new Date(vulnerability.detected_at), "d MMM yyyy", {
                    locale: es,
                  })}
                </span>
              </div>
              {vulnerability.resolved_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground text-sm">
                    Resuelta
                  </span>
                  <span className="text-sm font-medium">
                    {format(new Date(vulnerability.resolved_at), "d MMM yyyy", {
                      locale: es,
                    })}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-muted-foreground text-sm">
                  Actualizada
                </span>
                <span className="text-sm font-medium">
                  {format(new Date(vulnerability.updated_at), "d MMM yyyy", {
                    locale: es,
                  })}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
