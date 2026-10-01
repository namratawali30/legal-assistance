import { test, expect } from "@playwright/test";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.describe("Simple / Detailed Answer Mode E2E Suite", () => {
  test("Default mode is Simple, toggle to Detailed persists across refresh", async ({ page }) => {
    await registerAndLoginUser(page);

    await page.goto("/chat");
    const newChatBtn = page.getByRole("button", { name: /(\+ New legal chat|Start a legal chat)/i }).first();
    await newChatBtn.click();
    const titleInput = page.getByLabel(/chat title/i);
    await expect(titleInput).toBeVisible();
    await titleInput.fill("Answer Mode Test Chat");
    await page.getByRole("button", { name: /create chat/i }).click();

    // Verify default Simple button state
    const simpleBtn = page.getByRole("button", { name: /^Simple$/i });
    const detailedBtn = page.getByRole("button", { name: /^Detailed$/i });
    await expect(simpleBtn).toBeVisible();

    // Switch to Detailed mode
    await detailedBtn.click();

    // Reload page and verify Detailed mode choice persists
    await page.reload();
    await page.getByRole("button", { name: /Answer Mode Test Chat/i }).click();
    await expect(detailedBtn).toHaveClass(/bg-white/);

    // Switch back to Simple mode
    await simpleBtn.click();
    await expect(simpleBtn).toHaveClass(/bg-white/);
  });
});
