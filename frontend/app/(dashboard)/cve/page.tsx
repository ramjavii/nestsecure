'use client';

import { useState, useCallback } from 'react';
import { useCVESearch, useCVEStats } from '@/hooks/use-cve';
import {
  CVESearchForm,
  CVECardMinimal,
  CVEStatsCard,
} from '@/components/cve';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { 
  Database, 
  Shield, 
  Bug, 
  AlertTriangle,
  RefreshCw,
  Download,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Search,
  Filter,
} from 'lucide-react';
import type { CVESearchParams } from '@/types';

export default function CVESearchPage() {
  const [searchParams, setSearchParams] = useState<CVESearchParams>({
    page: 1,
    page_size: 20,
  });
  const [showFilters, setShowFilters] = useState(false);

  const { cves, total, page, pages, isLoading, error, refetch } = useCVESearch(searchParams);
  const { stats, isLoading: statsLoading, refetch: refetchStats } = useCVEStats();

  const handleSearch = useCallback((params: CVESearchParams) => {
    setSearchParams({ ...params, page: 1, page_size: 20 });
  }, []);

  const handlePageChange = useCallback((newPage: number) => {
    setSearchParams(prev => ({ ...prev, page: newPage }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleRefresh = useCallback(() => {
    refetch();
    refetchStats();
  }, [refetch, refetchStats]);

  const renderPagination = () => {
    if (pages <= 1) return null;

    const pageNumbers: number[] = [];
    const maxVisiblePages = 5;
    
    let startPage = Math.max(1, page - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(pages, startPage + maxVisiblePages - 1);
    
    if (endPage - startPage + 1 < maxVisiblePages) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
      pageNumbers.push(i);
    }

    return (
      <div className="flex items-center justify-between mt-6" data-testid="pagination">
        <p className="text-sm text-muted-foreground">
          Mostrando {((page - 1) * 20) + 1} a {Math.min(page * 20, total)} de {total.toLocaleString()} resultados
        </p>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            onClick={() => handlePageChange(1)}
            disabled={page === 1}
            title="Primera página"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => handlePageChange(page - 1)}
            disabled={page === 1}
            title="Página anterior"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          
          {startPage > 1 && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(1)}
              >
                1
              </Button>
              {startPage > 2 && <span className="px-2 text-muted-foreground">...</span>}
            </>
          )}
          
          {pageNumbers.map(pageNum => (
            <Button
              key={pageNum}
              variant={pageNum === page ? 'default' : 'outline'}
              size="sm"
              onClick={() => handlePageChange(pageNum)}
            >
              {pageNum}
            </Button>
          ))}
          
          {endPage < pages && (
            <>
              {endPage < pages - 1 && <span className="px-2 text-muted-foreground">...</span>}
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(pages)}
              >
                {pages}
              </Button>
            </>
          )}
          
          <Button
            variant="outline"
            size="icon"
            onClick={() => handlePageChange(page + 1)}
            disabled={page === pages}
            title="Página siguiente"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => handlePageChange(pages)}
            disabled={page === pages}
            title="Última página"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold" data-testid="page-title">CVE Database</h1>
          <p className="text-muted-foreground mt-2">
            Busca y explora Common Vulnerabilities and Exposures (CVEs) de la National Vulnerability Database
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            variant="outline" 
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="stats-cards">
        {statsLoading ? (
          <>
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
            <Skeleton className="h-28" />
          </>
        ) : stats ? (
          <>
            <Card data-testid="stat-total">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total CVEs</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total_cves?.toLocaleString() || '0'}</div>
                <p className="text-xs text-muted-foreground">
                  {stats.avg_cvss ? `CVSS promedio: ${stats.avg_cvss.toFixed(1)}` : 'Sin datos'}
                </p>
              </CardContent>
            </Card>
            
            <Card data-testid="stat-exploits">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Con Exploits</CardTitle>
                <Bug className="h-4 w-4 text-red-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">
                  {stats.with_exploits?.toLocaleString() || '0'}
                </div>
                <p className="text-xs text-muted-foreground">
                  {stats.total_cves > 0 
                    ? `${((stats.with_exploits / stats.total_cves) * 100).toFixed(1)}% del total`
                    : 'N/A'
                  }
                </p>
              </CardContent>
            </Card>
            
            <Card data-testid="stat-kev">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">En CISA KEV</CardTitle>
                <AlertTriangle className="h-4 w-4 text-orange-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-orange-600">
                  {stats.in_kev?.toLocaleString() || '0'}
                </div>
                <p className="text-xs text-muted-foreground">
                  Known Exploited Vulnerabilities
                </p>
              </CardContent>
            </Card>
            
            <Card data-testid="stat-sync">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Última Sync</CardTitle>
                <Shield className="h-4 w-4 text-green-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stats.last_sync 
                    ? new Date(stats.last_sync).toLocaleDateString('es-ES')
                    : 'Nunca'
                  }
                </div>
                <p className="text-xs text-muted-foreground">
                  Estado: {stats.sync_status || 'Desconocido'}
                </p>
              </CardContent>
            </Card>
          </>
        ) : (
          <Card className="col-span-4 p-6 text-center">
            <p className="text-muted-foreground">No hay estadísticas disponibles</p>
          </Card>
        )}
      </div>

      {/* Search Form */}
      <Card data-testid="search-form-card">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center gap-2">
              <Search className="h-5 w-5" />
              Buscar CVEs
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="h-4 w-4 mr-2" />
              {showFilters ? 'Ocultar Filtros' : 'Mostrar Filtros'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className={!showFilters ? 'pb-4' : undefined}>
          <CVESearchForm 
            onSearch={handleSearch} 
            isLoading={isLoading}
            compact={!showFilters}
          />
        </CardContent>
      </Card>

      {/* Active Filters */}
      {(searchParams.search || searchParams.severity || searchParams.has_exploit || searchParams.in_cisa_kev) && (
        <div className="flex items-center gap-2 flex-wrap" data-testid="active-filters">
          <span className="text-sm text-muted-foreground">Filtros activos:</span>
          {searchParams.search && (
            <Badge variant="secondary">
              Búsqueda: {searchParams.search}
            </Badge>
          )}
          {searchParams.severity && (
            <Badge variant="secondary">
              Severidad: {searchParams.severity}
            </Badge>
          )}
          {searchParams.has_exploit && (
            <Badge variant="destructive">
              Con Exploit
            </Badge>
          )}
          {searchParams.in_cisa_kev && (
            <Badge variant="outline" className="border-orange-500 text-orange-500">
              En CISA KEV
            </Badge>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSearchParams({ page: 1, page_size: 20 })}
          >
            Limpiar filtros
          </Button>
        </div>
      )}

      {/* Results */}
      <div data-testid="results-section">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">
            {total > 0 
              ? `Resultados (${total.toLocaleString()} encontrados)` 
              : 'Resultados'
            }
          </h2>
          {total > 0 && (
            <p className="text-sm text-muted-foreground">
              Página {page} de {pages}
            </p>
          )}
        </div>

        {error && (
          <Alert variant="destructive" className="mb-4" data-testid="error-alert">
            <AlertDescription>
              Error al cargar CVEs: {error.message}
            </AlertDescription>
          </Alert>
        )}

        {isLoading ? (
          <div className="space-y-2" data-testid="loading-skeleton">
            {[...Array(10)].map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
        ) : cves.length > 0 ? (
          <>
            <div className="space-y-2" data-testid="cve-list">
              {cves.map(cve => (
                <CVECardMinimal 
                  key={cve.cve_id} 
                  cve={cve}
                  data-testid="cve-card"
                />
              ))}
            </div>

            {/* Pagination */}
            {renderPagination()}
          </>
        ) : (
          <Card className="p-12 text-center" data-testid="empty-state">
            <Database className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No se encontraron CVEs</h3>
            <p className="text-muted-foreground mb-4">
              Intenta ajustar los filtros de búsqueda o los términos
            </p>
            <Button 
              variant="outline"
              onClick={() => setSearchParams({ page: 1, page_size: 20 })}
            >
              Restablecer búsqueda
            </Button>
          </Card>
        )}
      </div>
    </div>
  );
}
