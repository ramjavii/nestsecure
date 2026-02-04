'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bell, Search, Menu, User, Settings, LogOut, ChevronRight, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { ConnectionStatus } from '@/components/shared/connection-status';
import { useAuth } from '@/hooks/use-auth';
import { cn } from '@/lib/utils';

interface TopbarProps {
  onMenuClick: () => void;
  sidebarCollapsed: boolean;
}

const routeLabels: Record<string, string> = {
  dashboard: 'Dashboard',
  scans: 'Escaneos',
  assets: 'Assets',
  vulnerabilities: 'Vulnerabilidades',
  reports: 'Reportes',
  settings: 'Configuración',
};

export function Topbar({ onMenuClick, sidebarCollapsed }: TopbarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');

  const pathSegments = pathname.split('/').filter(Boolean);
  
  const breadcrumbs = pathSegments.map((segment, index) => {
    const path = '/' + pathSegments.slice(0, index + 1).join('/');
    const label = routeLabels[segment] || segment;
    const isLast = index === pathSegments.length - 1;
    
    // Check if it's an ID (UUID-like or numeric)
    const isId = /^[0-9a-f-]{8,}$/i.test(segment) || /^\d+$/.test(segment);
    
    return {
      path,
      label: isId ? 'Detalle' : label,
      isLast,
    };
  });

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <header
      className={cn(
        'fixed top-0 right-0 z-30 h-16 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 transition-all duration-300',
        sidebarCollapsed ? 'left-16' : 'left-64'
      )}
    >
      <div className="flex items-center justify-between h-full px-4 lg:px-6">
        {/* Left section - Mobile menu + Breadcrumb */}
        <div className="flex items-center gap-4">
          {/* Mobile menu button */}
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={onMenuClick}
          >
            <Menu className="h-5 w-5" />
          </Button>

          {/* Breadcrumb */}
          <nav className="hidden sm:flex items-center gap-1 text-sm">
            <Link
              href="/dashboard"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <Home className="h-4 w-4" />
            </Link>
            {breadcrumbs.map((crumb, index) => (
              <div key={crumb.path} className="flex items-center gap-1">
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
                {crumb.isLast ? (
                  <span className="font-medium text-foreground">{crumb.label}</span>
                ) : (
                  <Link
                    href={crumb.path}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {crumb.label}
                  </Link>
                )}
              </div>
            ))}
          </nav>
        </div>

        {/* Right section - Connection + Search + Notifications + User */}
        <div className="flex items-center gap-2 lg:gap-4">
          {/* Connection Status */}
          <ConnectionStatus className="hidden sm:flex" />

          {/* Search */}
          <div className="relative hidden md:block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Buscar..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64 pl-9 h-9 bg-muted/50"
            />
          </div>

          {/* Notifications */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                <Badge className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-[10px] bg-destructive text-destructive-foreground">
                  3
                </Badge>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <DropdownMenuLabel>Notificaciones</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <div className="max-h-64 overflow-y-auto">
                <DropdownMenuItem className="flex flex-col items-start gap-1 py-3 cursor-pointer">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-severity-critical" />
                    <span className="font-medium text-sm">Vulnerabilidad Crítica</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    Se detectó CVE-2024-1234 en servidor-prod-01
                  </span>
                  <span className="text-xs text-muted-foreground">hace 5 min</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="flex flex-col items-start gap-1 py-3 cursor-pointer">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-status-success" />
                    <span className="font-medium text-sm">Escaneo completado</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    Escaneo de red interna finalizado exitosamente
                  </span>
                  <span className="text-xs text-muted-foreground">hace 15 min</span>
                </DropdownMenuItem>
                <DropdownMenuItem className="flex flex-col items-start gap-1 py-3 cursor-pointer">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-status-warning" />
                    <span className="font-medium text-sm">Asset inactivo</span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    No se puede alcanzar 192.168.1.100
                  </span>
                  <span className="text-xs text-muted-foreground">hace 1 hora</span>
                </DropdownMenuItem>
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-center text-sm text-primary cursor-pointer justify-center">
                Ver todas las notificaciones
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* User menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-9 px-2 gap-2">
                <Avatar className="h-7 w-7">
                  <AvatarFallback className="bg-primary/10 text-primary text-xs font-medium">
                    {user?.full_name ? getInitials(user.full_name) : 'U'}
                  </AvatarFallback>
                </Avatar>
                <span className="hidden lg:block text-sm font-medium">
                  {user?.full_name || 'Usuario'}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium">{user?.full_name || 'Usuario'}</p>
                  <p className="text-xs text-muted-foreground">{user?.email}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/settings" className="cursor-pointer">
                  <User className="mr-2 h-4 w-4" />
                  Perfil
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/settings" className="cursor-pointer">
                  <Settings className="mr-2 h-4 w-4" />
                  Configuración
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive cursor-pointer"
                onClick={logout}
              >
                <LogOut className="mr-2 h-4 w-4" />
                Cerrar sesión
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
