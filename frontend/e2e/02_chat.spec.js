import { test, expect } from "@playwright/test";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.describe("Legal Chat E2E Suite", () => {
  test("Create chat session, send message, receive grounded answer, verify persistence", async ({ page }) => {
    await registerAndLoginUser(page);

    await page.goto("/chat");
    await expect(page).toHaveURL(/\/chat/);

    // Create new chat session if modal opens or click + New
    if (await page.getByRole("button", { name: /\+ New legal chat/i }).isVisible()) {
      await page.getByRole("button", { name: /\+ New legal chat/i }).click();
    } else if (await page.getByRole("button", { name: /Start a legal chat/i }).isVisible()) {
      await page.getByRole("button", { name: /Start a legal chat/i }).click();
    }

    await page.getByLabel(/chat title/i).fill("Defective Phone Refund Question");
    await page.getByRole("button", { name: /create chat/i }).click();

    // Send question
    const composer = page.getByLabel(/ask a legal-information question/i);
    await composer.fill("I bought a defective phone and the seller refuses to repair or refund.");
    await page.getByRole("button", { name: /send/i }).click();

    // Verify assistant answer appears with legal content and citation
    await expect(page.getByText(/consumers are protected/i)).toBeVisible({ timeout: 25000 });
    await expect(page.getByText(/\[SOURCE_1\]/i)).toBeVisible();

    // Refresh page and verify message history persists
    await page.reload();
    await page.getByRole("button", { name: /Defective Phone Refund Question/i }).click();
    await expect(page.getByText(/I bought a defective phone/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/consumers are protected/i)).toBeVisible();
  });
});
