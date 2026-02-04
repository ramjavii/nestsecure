'use client';

import React from "react"
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [isChecking, setIsChecking] = useState(true);
  const { accessToken, user } = useAuthStore();

  useEffect(() => {
    // Si hay token y user, redirigir al dashboard
    if (accessToken && user) {
      router.push('/');
      return;
    }
    // Si no hay token, mostrar login
    setIsChecking(false);
  }, [accessToken, user, router]);

  // Mostrar loading mientras verifica
  if (isChecking && accessToken) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse flex items-center gap-2 text-primary">
          <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          <span className="text-muted-foreground">Cargando...</span>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
