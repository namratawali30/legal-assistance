import { test, expect } from "@playwright/test";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.describe("Security Boundaries & Fail-Closed E2E Suite", () => {
  test("Unsupported query receives safe refusal message without fabricated law", async ({ page }) => {
    await registerAndLoginUser(page);

    await page.goto("/chat");
    const newChatBtn = page.getByRole("button", { name: /(\+ New legal chat|Start a legal chat)/i }).first();
    await newChatBtn.click();
    const titleInput = page.getByLabel(/chat title/i);
    await expect(titleInput).toBeVisible();
    await titleInput.fill("Unsupported Prompt Test");
    await page.getByRole("button", { name: /create chat/i }).click();

    const composer = page.getByLabel(/ask a legal-information question/i);
    await composer.fill("What is the penalty under martian law for speed flying? (unsupported_query)");
    await page.getByRole("button", { name: /send/i }).click();

    await expect(page.getByText(/could not find sufficiently relevant|refuse/i).first()).toBeVisible({ timeout: 25000 });
  });

  test("User B cannot access User A chat session", async ({ page }) => {
    // User A creates chat
    await registerAndLoginUser(page);
    await page.goto("/chat");
    const newChatBtn = page.getByRole("button", { name: /(\+ New legal chat|Start a legal chat)/i }).first();
    await newChatBtn.click();
    const titleInput = page.getByLabel(/chat title/i);
    await expect(titleInput).toBeVisible();
    await titleInput.fill("User A Private Chat");
    await page.getByRole("button", { name: /create chat/i }).click();
    const userAChatUrl = page.url();

    // User B registers and attempts to access User A's chat URL
    await page.getByRole("button", { name: /sign out/i }).click();
    await registerAndLoginUser(page);

    // Direct navigation to User A chat URL
    await page.goto(userAChatUrl);
    // Should fail/not load User A chat title or redirect cleanly
    await expect(page.getByText("User A Private Chat")).not.toBeVisible();
  });

  test("XSS payload is safely encoded and displayed as plain text", async ({ page }) => {
    await registerAndLoginUser(page);

    await page.goto("/chat");
    const newChatBtn = page.getByRole("button", { name: /(\+ New legal chat|Start a legal chat)/i }).first();
    await newChatBtn.click();
    const titleInput = page.getByLabel(/chat title/i);
    await expect(titleInput).toBeVisible();
    await titleInput.fill('<script>alert("xss-title")</script>');
    await page.getByRole("button", { name: /create chat/i }).click();

    const composer = page.getByLabel(/ask a legal-information question/i);
    await composer.fill('<script>alert("xss-message")</script>');
    await page.getByRole("button", { name: /send/i }).click();

    // Verify text is displayed as literal text content without executing alert
    await expect(page.getByText('<script>alert("xss-message")</script>')).toBeVisible();
  });
});
