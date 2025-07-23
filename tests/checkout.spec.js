import { test, expect } from "appwright";

test('checkout process', async ({ device }) => {
  await device.goto('https://example.com/checkout');
  await device.getByTestId('card-number').fill('4111111111111111');
  await device.getByTestId('expiry').fill('12/25');
  await device.getByTestId('cvv').fill('123');
  await device.getByTestId('pay-button').tap();
  await expect(device.getByTestId('success')).toBeVisible();
});
