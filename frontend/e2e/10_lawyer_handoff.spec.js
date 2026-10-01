import { test, expect } from "@playwright/test";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.describe("Lawyer Handoff Pack E2E Suite", () => {
  test("Open Lawyer Handoff modal, verify case summary sections and PDF/DOCX downloads", async ({ page }) => {
    test.setTimeout(60000);
    await registerAndLoginUser(page);

    await page.goto("/chat");
    const newChatBtn = page.getByRole("button", { name: /(\+ New legal chat|Start a legal chat)/i }).first();
    await newChatBtn.click();
    const titleInput = page.getByLabel(/chat title/i);
    await expect(titleInput).toBeVisible();
    await titleInput.fill("Handoff Pack Test Chat");
    await page.getByRole("button", { name: /create chat/i }).click();

    const composer = page.getByLabel(/ask a legal-information question/i);
    await composer.fill("I bought a defective product on 10 Jan 2026 for Rs 50,000 and the seller refuses to refund under Consumer Protection Act.");
    await page.getByRole("button", { name: /send/i }).click();
    await expect(page.getByText(/\[SOURCE_1\]/i)).toBeVisible({ timeout: 35000 });

    // Open Lawyer Handoff modal
    const handoffBtn = page.getByRole("button", { name: /lawyer handoff/i });
    if (!await handoffBtn.isVisible()) {
      await page.getByRole("button", { name: /actions/i }).click();
    }
    await page.getByRole("button", { name: /lawyer handoff/i }).click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("heading", { name: /lawyer handoff pack/i })).toBeVisible();
    await expect(dialog.getByText(/case summary/i).first()).toBeVisible({ timeout: 10000 });

    // Verify PDF Download
    const pdfPromise = page.waitForEvent("download");
    await dialog.getByRole("button", { name: /download pdf/i }).click();
    const pdfDownload = await pdfPromise;
    expect(pdfDownload.suggestedFilename()).toMatch(/\.pdf$/i);

    // Verify DOCX Download
    const docxPromise = page.waitForEvent("download");
    await dialog.getByRole("button", { name: /download docx/i }).click();
    const docxDownload = await docxPromise;
    expect(docxDownload.suggestedFilename()).toMatch(/\.docx$/i);

    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
  });
});
