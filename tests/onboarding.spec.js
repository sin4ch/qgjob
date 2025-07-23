const { test, expect } = require('@playwright/test');

test('user onboarding flow', async ({ page }) => {
  await page.goto('https://example.com');
  await page.click('[data-testid="get-started"]');
  await page.fill('[data-testid="email"]', 'test@example.com');
  await page.click('[data-testid="submit"]');
  await expect(page.locator('[data-testid="welcome"]')).toBeVisible();
});
