import { test, expect } from "@playwright/test";
import path from "node:path";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.describe("Document Evidence Vault E2E Suite", () => {
  test("Upload TXT document evidence, process, verify ready status and download", async ({ page }) => {
    test.setTimeout(60000);
    await registerAndLoginUser(page);

    await page.goto("/evidence");
    await expect(page).toHaveURL(/\/evidence/);

    // Open upload form
    await page.locator("#upload-evidence-btn").click();

    // Fill title & select file
    await page.getByLabel(/title/i).first().fill("Purchase Receipt Document");
    const filePath = path.resolve("e2e/fixtures/sample_doc.txt");
    await page.setInputFiles("input[type=file]", filePath);

    await page.getByRole("button", { name: /upload file/i }).click();

    // Verify evidence listed in vault
    await expect(page.getByText(/purchase receipt document/i).first()).toBeVisible({ timeout: 10000 });

    // Click item to view details
    await page.getByRole("button", { name: /purchase receipt document/i }).first().click();
    await expect(page.getByText(/sha-256 hash/i).first()).toBeVisible();

    // Click Process Evidence if not already ready
    const processBtn = page.getByRole("button", { name: /^Process$/i });
    if (await processBtn.isVisible()) {
      await processBtn.click();
    }

    await expect(page.getByText(/ready/i).first()).toBeVisible({ timeout: 15000 });

    // Download evidence file
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /^Download$/i }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/sample_doc/i);
  });
});
