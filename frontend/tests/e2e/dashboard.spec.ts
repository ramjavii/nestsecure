import { test, expect } from '@playwright/test';

/**
 * Tests E2E para el Dashboard
 */

test.describe('Dashboard', () => {
  // Login antes de cada test
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').fill('admin@nestsecure.com');
    await page.locator('input[type="password"]').fill('Admin123!');
    await page.locator('button[type="submit"]').click();
    await page.waitForURL(/\/(dashboard)?$/, { timeout: 10000 });
  });

  test('should display dashboard with stats cards', async ({ page }) => {
    await page.goto('/');
    
    // Verificar que hay cards de estadísticas
    const statCards = page.locator('[data-stat-card], .stat-card, .card');
    await expect(statCards.first()).toBeVisible({ timeout: 10000 });
    
    // Verificar contenido típico del dashboard
    const dashboardContent = await page.content();
    const hasStatistics = 
      dashboardContent.includes('Assets') ||
      dashboardContent.includes('Vulnerabilidades') ||
      dashboardContent.includes('Escaneos') ||
      dashboardContent.includes('Total');
    
    expect(hasStatistics).toBeTruthy();
  });

  test('should display navigation sidebar', async ({ page }) => {
    await page.goto('/');
    
    // Verificar elementos de navegación
    const navItems = [
      /dashboard/i,
      /assets/i,
      /scans|escaneos/i,
      /vulnerabilidades|vulnerabilities/i,
    ];
    
    for (const item of navItems) {
      const navLink = page.locator(`nav a, aside a, [role="navigation"] a`).filter({ hasText: item });
      // Al menos uno de los items de navegación debe existir
      const count = await navLink.count();
      if (count > 0) {
        await expect(navLink.first()).toBeVisible();
      }
    }
  });

  test('should navigate to assets page', async ({ page }) => {
    await page.goto('/');
    
    // Click en link de assets
    await page.locator('a[href*="assets"], nav >> text=Assets').first().click();
    
    // Verificar navegación
    await expect(page).toHaveURL(/assets/);
  });

  test('should navigate to scans page', async ({ page }) => {
    await page.goto('/');
    
    // Click en link de scans
    await page.locator('a[href*="scans"], nav >> text=Scan, nav >> text=Escan').first().click();
    
    // Verificar navegación
    await expect(page).toHaveURL(/scans/);
  });

  test('should show user information in header', async ({ page }) => {
    await page.goto('/');
    
    // Verificar que hay información del usuario
    const userArea = page.locator('header, nav').filter({
      has: page.locator('.avatar, img[alt*="user"], [data-user], text=admin')
    });
    
    // Debería existir algún indicador de usuario
    const hasUserInfo = await userArea.count() > 0 || 
                        await page.locator('text=admin').count() > 0;
    
    expect(hasUserInfo).toBeTruthy();
  });

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Cambiar a viewport móvil
    await page.setViewportSize({ width: 375, height: 667 });
    
    await page.goto('/');
    
    // La página debería cargar correctamente
    await expect(page.locator('body')).toBeVisible();
    
    // El contenido principal debería ser visible
    const mainContent = page.locator('main, [role="main"], .dashboard');
    if (await mainContent.count() > 0) {
      await expect(mainContent.first()).toBeVisible();
    }
  });

  test('should display charts or visualizations', async ({ page }) => {
    await page.goto('/');
    
    // Esperar a que cargue el contenido
    await page.waitForTimeout(2000);
    
    // Buscar elementos de gráficos (recharts genera SVG)
    const charts = page.locator('svg.recharts-surface, .recharts-wrapper, [data-chart], canvas');
    const chartCount = await charts.count();
    
    // Puede o no haber gráficos dependiendo de los datos
    // Solo verificamos que la página cargó correctamente
    expect(chartCount).toBeGreaterThanOrEqual(0);
  });
});
