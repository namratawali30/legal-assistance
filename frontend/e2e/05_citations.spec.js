import { test, expect } from "@playwright/test";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.describe("Interactive Citations E2E Suite", () => {
  test("Clicking citation opens SourceDetailsModal, Escape key closes modal", async ({ page }) => {
    await registerAndLoginUser(page);

    await page.goto("/chat");
    const newChatBtn = page.getByRole("button", { name: /(\+ New legal chat|Start a legal chat)/i }).first();
    await newChatBtn.click();
    const titleInput = page.getByLabel(/chat title/i);
    await expect(titleInput).toBeVisible();
    await titleInput.fill("Citation Modal Test");
    await page.getByRole("button", { name: /create chat/i }).click();

    // Ask question to receive grounded answer
    const composer = page.getByLabel(/ask a legal-information question/i);
    await composer.fill("How can I file a consumer complaint?");
    await page.getByRole("button", { name: /send/i }).click();

    await expect(page.getByText(/\[SOURCE_1\]/i)).toBeVisible({ timeout: 25000 });

    // Open source drawer and click source card
    const viewSourcesBtn = page.getByRole("button", { name: /sources used/i });
    await viewSourcesBtn.click();

    const sourceCard = page.getByText(/View details|Official Source|SOURCE_1/i).last();
    await sourceCard.click();

    // Verify SourceDetailsModal opens with role="dialog" and heading
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(/legal source details|source details/i)).toBeVisible();

    // Press Escape to close modal
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
  });
});
