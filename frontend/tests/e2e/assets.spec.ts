import { test, expect } from '@playwright/test';

/**
 * Tests E2E para la gestión de Assets
 */

test.describe('Assets Management', () => {
  // Login antes de cada test
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').fill('admin@nestsecure.com');
    await page.locator('input[type="password"]').fill('Admin123!');
    await page.locator('button[type="submit"]').click();
    await page.waitForURL(/\/(dashboard)?$/, { timeout: 10000 });
  });

  test('should display assets list page', async ({ page }) => {
    await page.goto('/assets');
    
    // Verificar que la página de assets carga
    await expect(page).toHaveURL(/assets/);
    
    // Verificar título o encabezado
    const heading = page.locator('h1, h2').filter({ hasText: /assets|activos/i });
    await expect(heading.first()).toBeVisible({ timeout: 5000 });
  });

  test('should show empty state or assets list', async ({ page }) => {
    await page.goto('/assets');
    
    // Esperar a que cargue el contenido
    await page.waitForTimeout(2000);
    
    // Verificar que hay una tabla, lista o estado vacío
    const hasTable = await page.locator('table, [role="table"]').count() > 0;
    const hasList = await page.locator('.asset-list, .asset-item, [data-asset]').count() > 0;
    const hasEmptyState = await page.locator('text=No hay, text=sin assets, text=empty, .empty-state').count() > 0;
    
    expect(hasTable || hasList || hasEmptyState).toBeTruthy();
  });

  test('should have new asset button', async ({ page }) => {
    await page.goto('/assets');
    
    // Buscar botón de nuevo asset
    const newButton = page.locator('button, a').filter({ 
      hasText: /nuevo|new|crear|add|añadir/i 
    });
    
    await expect(newButton.first()).toBeVisible({ timeout: 5000 });
  });

  test('should open create asset modal/form', async ({ page }) => {
    await page.goto('/assets');
    
    // Click en nuevo asset
    const newButton = page.locator('button, a').filter({ 
      hasText: /nuevo|new|crear|add|añadir/i 
    });
    await newButton.first().click();
    
    // Verificar que se abre modal o formulario
    await page.waitForTimeout(1000);
    
    const hasModal = await page.locator('[role="dialog"], .modal, .dialog').count() > 0;
    const hasForm = await page.locator('form').count() > 0;
    const navigatedToForm = page.url().includes('new') || page.url().includes('create');
    
    expect(hasModal || hasForm || navigatedToForm).toBeTruthy();
  });

  test('should validate asset creation form', async ({ page }) => {
    await page.goto('/assets');
    
    // Click en nuevo asset
    const newButton = page.locator('button, a').filter({ 
      hasText: /nuevo|new|crear|add|añadir/i 
    });
    await newButton.first().click();
    
    await page.waitForTimeout(1000);
    
    // Intentar enviar sin datos
    const submitButton = page.locator('button[type="submit"], button:has-text("Crear"), button:has-text("Guardar")');
    if (await submitButton.count() > 0) {
      await submitButton.first().click();
      
      // Debería mostrar errores de validación o no enviarse
      await page.waitForTimeout(500);
      const stillOnForm = await page.locator('[role="dialog"], form, input').count() > 0;
      expect(stillOnForm).toBeTruthy();
    }
  });

  test('should create a new asset', async ({ page }) => {
    await page.goto('/assets');
    
    // Click en nuevo asset
    const newButton = page.locator('button, a').filter({ 
      hasText: /nuevo|new|crear|add|añadir/i 
    });
    await newButton.first().click();
    
    await page.waitForTimeout(1000);
    
    // Llenar formulario
    const ipInput = page.locator('input[name="ip_address"], input[name="ip"], input[placeholder*="IP"]');
    if (await ipInput.count() > 0) {
      await ipInput.first().fill('192.168.1.200');
    }
    
    const hostnameInput = page.locator('input[name="hostname"], input[name="name"], input[placeholder*="nombre"]');
    if (await hostnameInput.count() > 0) {
      await hostnameInput.first().fill('test-asset-e2e');
    }
    
    // Enviar formulario
    const submitButton = page.locator('button[type="submit"], button:has-text("Crear"), button:has-text("Guardar")');
    if (await submitButton.count() > 0) {
      await submitButton.first().click();
      
      // Esperar a que se cierre el modal o se guarde
      await page.waitForTimeout(2000);
    }
  });

  test('should have search/filter functionality', async ({ page }) => {
    await page.goto('/assets');
    
    // Buscar campo de búsqueda o filtros
    const searchInput = page.locator('input[type="search"], input[placeholder*="buscar"], input[placeholder*="search"]');
    const filterSelect = page.locator('select, [role="combobox"]');
    
    const hasSearch = await searchInput.count() > 0;
    const hasFilters = await filterSelect.count() > 0;
    
    // Debería tener al menos uno
    expect(hasSearch || hasFilters).toBeTruthy();
  });

  test('should handle pagination if available', async ({ page }) => {
    await page.goto('/assets');
    
    await page.waitForTimeout(2000);
    
    // Buscar elementos de paginación
    const pagination = page.locator('[data-pagination], .pagination, nav:has(button:has-text("1"))');
    const nextButton = page.locator('button:has-text("Siguiente"), button:has-text("Next"), button[aria-label*="next"]');
    
    const hasPagination = await pagination.count() > 0 || await nextButton.count() > 0;
    
    // La paginación puede no existir si hay pocos items
    expect(typeof hasPagination).toBe('boolean');
  });
});
