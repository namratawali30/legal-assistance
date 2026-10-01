import { test, expect } from "@playwright/test";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.use({ viewport: { width: 390, height: 844 } });

test.describe("Mobile Responsiveness E2E Suite", () => {
  test("Complete mobile workflow fits without horizontal scroll overflow", async ({ page }) => {
    test.setTimeout(60000);
    await registerAndLoginUser(page);

    // Verify mobile navigation drawer
    const hamburger = page.getByRole("button", { name: /open main menu/i });
    await expect(hamburger).toBeVisible();
    await hamburger.click();

    const mobileNav = page.getByRole("dialog");
    await expect(mobileNav).toBeVisible();
    await mobileNav.getByRole("link", { name: /legal chat/i }).first().click();

    await expect(page).toHaveURL(/\/chat/);

    // Open mobile chat sessions drawer or create chat directly
    const chatsBtn = page.getByRole("button", { name: /open chat history/i });
    if (await chatsBtn.isVisible()) {
      await chatsBtn.click();
      await page.getByRole("button", { name: /\+ new legal chat/i }).click();
    } else {
      await page.getByRole("button", { name: /(\+ new legal chat|\+ new)/i }).first().click();
    }
    await page.getByLabel(/chat title/i).fill("Mobile Test Query");
    await page.getByRole("button", { name: /create chat/i }).click();

    // Send question
    const composer = page.getByLabel(/ask a legal-information question/i);
    await composer.fill("I bought a defective product on 10 Jan 2026 for Rs 50,000 and the seller refuses to refund under Consumer Protection Act.");
    await page.getByRole("button", { name: /send/i }).click();

    await expect(page.getByText(/\[SOURCE_1\]/i)).toBeVisible({ timeout: 35000 });

    // Open Actions dropdown on mobile
    const actionsMenuBtn = page.getByRole("button", { name: /actions/i });
    await actionsMenuBtn.click();
    await expect(page.getByRole("button", { name: /lawyer handoff/i })).toBeVisible();

    // Verify document overflow fits mobile screen
    const isOverflowing = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth + 5;
    });
    expect(isOverflowing).toBe(false);
  });
});
