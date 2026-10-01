import { test, expect } from "@playwright/test";
import { generateTestUser } from "./helpers/test-utils.js";

test.describe("Authentication E2E Suite", () => {
  const user = generateTestUser();

  test("A. Register new user successfully", async ({ page }) => {
    await page.goto("/register");
    await expect(page.getByRole("heading", { name: /create your account/i })).toBeVisible();

    await page.getByLabel(/full name/i).fill(user.fullName);
    await page.getByLabel(/email address/i).fill(user.email);
    await page.getByLabel(/^password/i).fill(user.password);
    await page.getByLabel(/confirm password/i).fill(user.password);

    await page.getByRole("button", { name: /create account/i }).click();

    // After registration, user is redirected to /login
    await expect(page).toHaveURL(/\/login/);
  });

  test("B. Login with valid user credentials", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email address/i).fill(user.email);
    await page.getByLabel(/^password/i).fill(user.password);

    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/http:\/\/127\.0\.0\.1:5173\/?$/);
    await expect(page.getByText(user.fullName)).toBeVisible();
  });

  test("C. Invalid Login shows user-understandable error without crashing", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email address/i).fill(user.email);
    await page.getByLabel(/^password/i).fill("WrongPassword999!");

    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByRole("alert")).toContainText(/invalid|incorrect|could not|failed|error/i);
    await expect(page).toHaveURL(/\/login/);
  });

  test("D. Protected route redirects to login when unauthenticated", async ({ page }) => {
    await page.goto("/chat");
    await expect(page).toHaveURL(/\/login/);
  });

  test("E. Session restores after page refresh when authenticated", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email address/i).fill(user.email);
    await page.getByLabel(/^password/i).fill(user.password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/http:\/\/127\.0\.0\.1:5173\/?$/);

    await page.reload();
    await expect(page).toHaveURL(/http:\/\/127\.0\.0\.1:5173\/?$/);
    await expect(page.getByText(user.fullName)).toBeVisible();
  });

  test("F. Sign out clears session and prevents protected access", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel(/email address/i).fill(user.email);
    await page.getByLabel(/^password/i).fill(user.password);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page).toHaveURL(/http:\/\/127\.0\.0\.1:5173\/?$/);

    await page.getByRole("button", { name: /sign out/i }).click();
    await expect(page).toHaveURL(/\/login/);

    await page.goto("/chat");
    await expect(page).toHaveURL(/\/login/);
  });
});
