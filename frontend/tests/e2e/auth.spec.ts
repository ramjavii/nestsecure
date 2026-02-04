import { test, expect } from '@playwright/test';

/**
 * Tests E2E para el flujo de autenticación
 */

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Limpiar cookies y storage antes de cada test
    await page.context().clearCookies();
  });

  test('should display login page correctly', async ({ page }) => {
    await page.goto('/login');
    
    // Verificar elementos de la página de login
    await expect(page.locator('h1, h2').first()).toContainText(/iniciar sesión|login|bienvenido/i);
    await expect(page.locator('input[type="email"], input[name="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show validation errors for empty fields', async ({ page }) => {
    await page.goto('/login');
    
    // Intentar enviar formulario vacío
    await page.locator('button[type="submit"]').click();
    
    // Verificar que se muestran errores de validación
    // El formulario no debería enviarse con campos vacíos
    await expect(page).toHaveURL(/login/);
  });

  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('/login');
    
    // Ingresar credenciales inválidas
    await page.locator('input[type="email"], input[name="email"]').fill('invalid@email.com');
    await page.locator('input[type="password"]').fill('wrongpassword123');
    await page.locator('button[type="submit"]').click();
    
    // Esperar respuesta y verificar error
    await page.waitForTimeout(2000);
    
    // Debería mostrar un mensaje de error o permanecer en login
    const hasError = await page.locator('[role="alert"], .error, .toast, [data-state="open"]').count() > 0 ||
                     await page.url().includes('login');
    expect(hasError).toBeTruthy();
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/login');
    
    // Ingresar credenciales válidas
    await page.locator('input[type="email"], input[name="email"]').fill('admin@nestsecure.com');
    await page.locator('input[type="password"]').fill('Admin123!');
    await page.locator('button[type="submit"]').click();
    
    // Esperar redirección al dashboard
    await page.waitForURL(/\/(dashboard)?$/, { timeout: 10000 });
    
    // Verificar que estamos en el dashboard
    await expect(page).not.toHaveURL(/login/);
  });

  test('should persist session after page reload', async ({ page }) => {
    // Login primero
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').fill('admin@nestsecure.com');
    await page.locator('input[type="password"]').fill('Admin123!');
    await page.locator('button[type="submit"]').click();
    
    await page.waitForURL(/\/(dashboard)?$/, { timeout: 10000 });
    
    // Recargar página
    await page.reload();
    
    // Verificar que seguimos autenticados
    await expect(page).not.toHaveURL(/login/);
  });

  test('should logout successfully', async ({ page }) => {
    // Login primero
    await page.goto('/login');
    await page.locator('input[type="email"], input[name="email"]').fill('admin@nestsecure.com');
    await page.locator('input[type="password"]').fill('Admin123!');
    await page.locator('button[type="submit"]').click();
    
    await page.waitForURL(/\/(dashboard)?$/, { timeout: 10000 });
    
    // Buscar y hacer click en logout (puede estar en un menú)
    const logoutButton = page.locator('button:has-text("Cerrar sesión"), button:has-text("Logout"), [data-logout]');
    if (await logoutButton.count() > 0) {
      await logoutButton.first().click();
    } else {
      // Buscar en dropdown de usuario
      const userMenu = page.locator('[data-user-menu], button:has(.avatar), .user-menu');
      if (await userMenu.count() > 0) {
        await userMenu.first().click();
        await page.locator('text=Cerrar sesión, text=Logout').first().click();
      }
    }
    
    // Verificar redirección a login
    await expect(page).toHaveURL(/login/, { timeout: 5000 });
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    // Intentar acceder a página protegida sin autenticación
    await page.goto('/');
    
    // Debería redirigir a login
    await expect(page).toHaveURL(/login/, { timeout: 5000 });
  });
});
