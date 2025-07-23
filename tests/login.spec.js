import { test, expect } from "appwright";

test('user login', async ({ device }) => {
  await device.goto('https://example.com/login');
  await device.getByTestId('username').fill('testuser');
  await device.getByTestId('password').fill('password123');
  await device.getByTestId('login-button').tap();
  await expect(device.getByTestId('dashboard')).toBeVisible();
});
