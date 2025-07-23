import { test, expect } from "appwright";

test('user onboarding flow', async ({ device }) => {
  await device.goto('https://example.com');
  await device.getByTestId('get-started').tap();
  await device.getByTestId('email').fill('test@example.com');
  await device.getByTestId('submit').tap();
  await expect(device.getByTestId('welcome')).toBeVisible();
});
