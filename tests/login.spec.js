const { test, expect } = require('@playwright/test');

test('user login', async ({ page }) => {
  await page.goto('https://example.com/login');
  await page.fill('[data-testid="username"]', 'testuser');
  await page.fill('[data-testid="password"]', 'password123');
  await page.click('[data-testid="login-button"]');
  await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
});
