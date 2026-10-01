import { test, expect } from "@playwright/test";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.describe("Keyboard Accessibility E2E Suite", () => {
  test("Keyboard skip link focuses main landmark, Escape key closes modals", async ({ page }) => {
    test.setTimeout(60000);
    await registerAndLoginUser(page);

    await page.goto("/dashboard");

    // Focus skip link
    const skipLink = page.getByRole("link", { name: /skip to main content/i });
    await skipLink.focus();
    await expect(skipLink).toBeFocused();

    // Press Enter on skip link to navigate focus to main content
    await page.keyboard.press("Enter");
    const mainLandmark = page.locator("#main-content");
    await expect(mainLandmark).toBeFocused();

    // Navigate to Chat Page and test modal keyboard behavior
    await page.goto("/chat");
    const newChatBtn = page.getByRole("button", { name: /(\+ New legal chat|Start a legal chat)/i }).first();
    await newChatBtn.click();
    const titleInput = page.getByLabel(/chat title/i);
    await expect(titleInput).toBeVisible();
    await titleInput.fill("Keyboard Accessibility Chat");
    await page.getByRole("button", { name: /create chat/i }).click();

    const composer = page.getByLabel(/ask a legal-information question/i);
    await composer.fill("I bought a defective product on 10 Jan 2026 for Rs 50,000 and the seller refuses to refund under Consumer Protection Act.");
    await page.getByRole("button", { name: /send/i }).click();

    await expect(page.getByText(/\[SOURCE_1\]/i)).toBeVisible({ timeout: 35000 });

    // Open Action Plan modal
    const actionPlanBtn = page.getByRole("button", { name: /action plan/i });
    if (!await actionPlanBtn.isVisible()) {
      await page.getByRole("button", { name: /actions/i }).click();
    }
    await page.getByRole("button", { name: /action plan/i }).click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    // Close via Escape
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
  });
});
