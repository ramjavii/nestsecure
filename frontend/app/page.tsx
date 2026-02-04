'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/stores/auth-store';

export default function RootPage() {
  const router = useRouter();
  const { accessToken } = useAuthStore();

  useEffect(() => {
    // Redirigir basado en estado de autenticación
    if (accessToken) {
      // Si hay token, ir al dashboard
      // El dashboard layout verificará si es válido
      router.replace('/dashboard');
    } else {
      router.replace('/login');
    }
  }, [accessToken, router]);

  // Loading mientras decide a dónde ir
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <div className="h-10 w-10 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      </div>
    </div>
  );
}
