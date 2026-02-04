'use client';

import React from "react"

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';
import { api } from '@/lib/api';
import { Sidebar } from '@/components/layout/sidebar';
import { Topbar } from '@/components/layout/topbar';
import { cn } from '@/lib/utils';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const { accessToken, user, setUser, logout } = useAuthStore();
  const [isInitialized, setIsInitialized] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Initialize auth state
  useEffect(() => {
    const initAuth = async () => {
      if (!accessToken) {
        router.push('/login');
        return;
      }
      
      // Si ya tenemos user, no volver a llamar API
      if (user) {
        setIsInitialized(true);
        return;
      }
      
      try {
        const userData = await api.getMe();
        setUser(userData);
        setIsInitialized(true);
      } catch {
        logout();
        router.push('/login');
      }
    };

    initAuth();
  }, [accessToken, user, setUser, logout, router]);

  // Handle responsive sidebar
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setSidebarCollapsed(true);
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <span className="text-muted-foreground">Cargando...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar - hidden on mobile, shown on desktop */}
      <div className="hidden lg:block">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      {/* Mobile sidebar overlay */}
      {mobileMenuOpen && (
        <div className="lg:hidden">
          <div
            className="fixed inset-0 z-30 bg-background/80 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-40 w-64">
            <Sidebar collapsed={false} onToggle={() => setMobileMenuOpen(false)} />
          </div>
        </div>
      )}

      {/* Topbar */}
      <Topbar
        onMenuClick={() => setMobileMenuOpen(true)}
        sidebarCollapsed={sidebarCollapsed}
      />

      {/* Main content */}
      <main
        className={cn(
          'pt-16 min-h-screen transition-all duration-300',
          sidebarCollapsed ? 'lg:pl-16' : 'lg:pl-64'
        )}
      >
        <div className="p-4 lg:p-6">{children}</div>
      </main>
    </div>
  );
}
