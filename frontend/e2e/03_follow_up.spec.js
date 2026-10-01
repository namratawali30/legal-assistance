import { test, expect } from "@playwright/test";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.describe("Follow-Up Question Engine E2E Suite", () => {
  test("Ambiguous input triggers clarification UI, selecting option resolves ambiguity", async ({ page }) => {
    await registerAndLoginUser(page);

    await page.goto("/chat");
    const newChatBtn = page.getByRole("button", { name: /(\+ New legal chat|Start a legal chat)/i }).first();
    await newChatBtn.click();
    const titleInput = page.getByLabel(/chat title/i);
    await expect(titleInput).toBeVisible();
    await titleInput.fill("Senior Harassment Query");
    await page.getByRole("button", { name: /create chat/i }).click();

    // Ambiguous user question
    const composer = page.getByLabel(/ask a legal-information question/i);
    await composer.fill("My senior is forcing me to do his work.");
    await page.getByRole("button", { name: /send/i }).click();

    // Verify clarification UI appears with notice
    await expect(page.getByText(/clarification needed/i)).toBeVisible({ timeout: 25000 });

    // Option buttons should be visible
    const collegeOption = page.getByRole("button", { name: /senior student in my college/i });
    await expect(collegeOption).toBeVisible();

    // Click option
    await collegeOption.click();
    await page.getByRole("button", { name: /send/i }).click();

    // Substantive legal answer follows without clarification badge loop
    await expect(page.getByText(/consumers are protected|prohibited under law|handled under Anti-Ragging/i).first()).toBeVisible({ timeout: 25000 });
  });
});
