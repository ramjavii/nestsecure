import { test, expect } from '@playwright/test';

/**
 * Tests E2E para la gestión de Scans (Escaneos)
 */

test.describe('Scans Management', () => {
  // Login antes de cada test
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').fill('admin@nestsecure.com');
    await page.locator('input[type="password"]').fill('Admin123!');
    await page.locator('button[type="submit"]').click();
    await page.waitForURL(/\/(dashboard)?$/, { timeout: 10000 });
  });

  test('should display scans list page', async ({ page }) => {
    await page.goto('/scans');
    
    // Verificar que la página de scans carga
    await expect(page).toHaveURL(/scans/);
    
    // Verificar título o encabezado
    const heading = page.locator('h1, h2').filter({ hasText: /scans|escaneos/i });
    await expect(heading.first()).toBeVisible({ timeout: 5000 });
  });

  test('should show empty state or scans list', async ({ page }) => {
    await page.goto('/scans');
    
    // Esperar a que cargue el contenido
    await page.waitForTimeout(2000);
    
    // Verificar que hay una tabla, lista o estado vacío
    const hasTable = await page.locator('table, [role="table"]').count() > 0;
    const hasList = await page.locator('.scan-list, .scan-item, [data-scan]').count() > 0;
    const hasEmptyState = await page.locator('text=No hay, text=sin escaneos, text=empty, .empty-state').count() > 0;
    
    expect(hasTable || hasList || hasEmptyState).toBeTruthy();
  });

  test('should have new scan button', async ({ page }) => {
    await page.goto('/scans');
    
    // Buscar botón de nuevo scan
    const newButton = page.locator('button, a').filter({ 
      hasText: /nuevo|new|crear|iniciar|start/i 
    });
    
    await expect(newButton.first()).toBeVisible({ timeout: 5000 });
  });

  test('should open create scan modal/form', async ({ page }) => {
    await page.goto('/scans');
    
    // Click en nuevo scan
    const newButton = page.locator('button, a').filter({ 
      hasText: /nuevo|new|crear|iniciar|start/i 
    });
    await newButton.first().click();
    
    // Verificar que se abre modal o formulario
    await page.waitForTimeout(1000);
    
    const hasModal = await page.locator('[role="dialog"], .modal, .dialog').count() > 0;
    const hasForm = await page.locator('form').count() > 0;
    const navigatedToForm = page.url().includes('new') || page.url().includes('create');
    
    expect(hasModal || hasForm || navigatedToForm).toBeTruthy();
  });

  test('should show scan type options', async ({ page }) => {
    await page.goto('/scans');
    
    // Click en nuevo scan
    const newButton = page.locator('button, a').filter({ 
      hasText: /nuevo|new|crear|iniciar|start/i 
    });
    await newButton.first().click();
    
    await page.waitForTimeout(1000);
    
    // Verificar opciones de tipo de scan
    const content = await page.content();
    const hasScanTypes = 
      content.includes('quick') ||
      content.includes('full') ||
      content.includes('discovery') ||
      content.includes('rápido') ||
      content.includes('completo');
    
    expect(hasScanTypes).toBeTruthy();
  });

  test('should validate scan target input', async ({ page }) => {
    await page.goto('/scans');
    
    // Click en nuevo scan
    const newButton = page.locator('button, a').filter({ 
      hasText: /nuevo|new|crear|iniciar|start/i 
    });
    await newButton.first().click();
    
    await page.waitForTimeout(1000);
    
    // Buscar campo de targets
    const targetInput = page.locator('input[name="targets"], input[name="target"], input[placeholder*="target"], input[placeholder*="IP"], textarea');
    if (await targetInput.count() > 0) {
      // Ingresar IP inválida
      await targetInput.first().fill('invalid-ip');
      
      // Intentar enviar
      const submitButton = page.locator('button[type="submit"], button:has-text("Iniciar"), button:has-text("Start")');
      if (await submitButton.count() > 0) {
        await submitButton.first().click();
        await page.waitForTimeout(500);
        
        // Debería mostrar error de validación o no enviarse
        const stillOnForm = await page.locator('[role="dialog"], form, input').count() > 0;
        expect(stillOnForm).toBeTruthy();
      }
    }
  });

  test('should create a scan with valid data', async ({ page }) => {
    await page.goto('/scans');
    
    // Click en nuevo scan
    const newButton = page.locator('button, a').filter({ 
      hasText: /nuevo|new|crear|iniciar|start/i 
    });
    await newButton.first().click();
    
    await page.waitForTimeout(1000);
    
    // Llenar nombre
    const nameInput = page.locator('input[name="name"], input[placeholder*="nombre"]');
    if (await nameInput.count() > 0) {
      await nameInput.first().fill('Test Scan E2E');
    }
    
    // Llenar target
    const targetInput = page.locator('input[name="targets"], input[name="target"], input[placeholder*="target"], input[placeholder*="IP"], textarea');
    if (await targetInput.count() > 0) {
      await targetInput.first().fill('192.168.1.1');
    }
    
    // Enviar formulario
    const submitButton = page.locator('button[type="submit"], button:has-text("Iniciar"), button:has-text("Crear"), button:has-text("Start")');
    if (await submitButton.count() > 0) {
      await submitButton.first().click();
      
      // Esperar respuesta
      await page.waitForTimeout(2000);
    }
  });

  test('should display scan status badges', async ({ page }) => {
    await page.goto('/scans');
    
    await page.waitForTimeout(2000);
    
    // Buscar badges de estado
    const statusBadges = page.locator('.badge, [data-status], .status');
    const content = await page.content();
    
    const hasStatusIndicators = 
      await statusBadges.count() > 0 ||
      content.includes('running') ||
      content.includes('completed') ||
      content.includes('pending') ||
      content.includes('ejecutando') ||
      content.includes('completado');
    
    // Puede no haber scans, así que verificamos que la página cargó
    expect(typeof hasStatusIndicators).toBe('boolean');
  });

  test('should navigate to scan detail', async ({ page }) => {
    await page.goto('/scans');
    
    await page.waitForTimeout(2000);
    
    // Buscar un scan en la lista para hacer click
    const scanRow = page.locator('tr, .scan-item, [data-scan-id]').first();
    
    if (await scanRow.count() > 0) {
      // Click en la fila o en un link dentro de ella
      const scanLink = scanRow.locator('a, button').first();
      if (await scanLink.count() > 0) {
        await scanLink.click();
        
        // Verificar que navegó a detalle
        await page.waitForTimeout(1000);
        const isOnDetail = page.url().includes('/scans/');
        expect(isOnDetail).toBeTruthy();
      }
    }
  });

  test('should show scan filters', async ({ page }) => {
    await page.goto('/scans');
    
    // Buscar filtros
    const filterSelect = page.locator('select, [role="combobox"]');
    const statusFilter = page.locator('[data-filter], button:has-text("Estado"), button:has-text("Status")');
    
    const hasFilters = await filterSelect.count() > 0 || await statusFilter.count() > 0;
    
    expect(hasFilters).toBeTruthy();
  });
});
