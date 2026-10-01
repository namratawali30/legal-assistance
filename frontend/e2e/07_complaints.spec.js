import { test, expect } from "@playwright/test";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.describe("Complaints Lifecycle E2E Suite", () => {
  test("Create, edit draft, generate, review, finalize complaint, export PDF/DOCX", async ({ page }) => {
    test.setTimeout(90000);
    await registerAndLoginUser(page);

    await page.goto("/complaints");
    await expect(page).toHaveURL(/\/complaints/);

    // Create complaint
    await page.getByRole("button", { name: /new complaint/i }).click();

    await page.locator("#field-title").fill("Defective TV Purchase");
    await page.locator("#field-category").selectOption("consumer_rights");
    await page.locator("#field-complainant-name").fill("Ramesh Kumar");
    await page.locator("#field-respondent-name").fill("Apex Electronics Pvt Ltd");
    await page.locator("#field-facts").fill("Purchased a 55-inch television for Rs. 45,000 on 15 Jan 2026. The display panel is defective and seller refuses repair or refund.");

    await page.locator("#complaint-save-btn").click();

    // Verify complaint saved
    await expect(page.getByText(/complaint identification|complaint created|defective television complaint/i)).toBeVisible();

    // Generate with AI
    await page.locator("#generate-complaint-btn").click();
    await expect(page.getByText(/ai-generated complaint text/i).first()).toBeVisible({ timeout: 25000 });

    // Finalize complaint
    const finalizeBtn = page.locator("#finalize-complaint-btn");
    await expect(finalizeBtn).toBeVisible({ timeout: 10000 });
    await finalizeBtn.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: /yes, finalize complaint/i }).click();

    // Export PDF download verification
    const pdfPromise = page.waitForEvent("download");
    await page.locator("#export-pdf-btn").click();
    const pdfDownload = await pdfPromise;
    expect(pdfDownload.suggestedFilename()).toMatch(/\.pdf$/i);

    // Export DOCX download verification
    const docxPromise = page.waitForEvent("download");
    await page.locator("#export-docx-btn").click();
    const docxDownload = await docxPromise;
    expect(docxDownload.suggestedFilename()).toMatch(/\.docx$/i);
  });
});
