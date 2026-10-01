import { expect } from "@playwright/test";

export function generateTestUser() {
  const uniqueId = Date.now().toString(36) + Math.random().toString(36).substring(2, 7);
  return {
    fullName: `E2E Test User ${uniqueId}`,
    email: `e2e-user-${uniqueId}@example.com`,
    password: "TestPassword123!",
  };
}

export async function registerAndLoginUser(page, user = generateTestUser()) {
  await page.goto("/register");
  await page.getByLabel("Full name").fill(user.fullName);
  await page.getByLabel("Email address").fill(user.email);
  await page.getByLabel("Password", { exact: false }).first().fill(user.password);
  await page.getByLabel("Confirm password").fill(user.password);
  await page.getByRole("button", { name: "Create account", exact: true }).click();

  // After registration, user is redirected to /login
  await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

  await page.getByLabel("Email address").fill(user.email);
  await page.getByLabel("Password", { exact: false }).first().fill(user.password);
  await page.getByRole("button", { name: /sign in/i }).click();

  // After login, lands on root / (Dashboard)
  await expect(page).toHaveURL(/http:\/\/127\.0\.0\.1:5173\/?$/, { timeout: 10000 });

  return user;
}
