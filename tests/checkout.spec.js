const { test, expect } = require('@playwright/test');

test('checkout process', async ({ page }) => {
  await page.goto('https://example.com/checkout');
  await page.fill('[data-testid="card-number"]', '4111111111111111');
  await page.fill('[data-testid="expiry"]', '12/25');
  await page.fill('[data-testid="cvv"]', '123');
  await page.click('[data-testid="pay-button"]');
  await expect(page.locator('[data-testid="success"]')).toBeVisible();
});
