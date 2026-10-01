import { test, expect } from "@playwright/test";
import path from "node:path";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.describe("Audio & Video Evidence Vault E2E Suite", () => {
  test("Upload and process Audio evidence, verify AI transcript warning", async ({ page }) => {
    test.setTimeout(60000);
    await registerAndLoginUser(page);

    await page.goto("/evidence");
    await page.locator("#upload-evidence-btn").click();

    await page.getByLabel(/title/i).first().fill("Seller Call Recording");
    const audioPath = path.resolve("e2e/fixtures/sample_audio.mp3");
    await page.setInputFiles("input[type=file]", audioPath);
    await page.getByRole("button", { name: /upload file/i }).click();

    await expect(page.getByText(/seller call recording/i).first()).toBeVisible({ timeout: 10000 });
    await page.getByRole("button", { name: /seller call recording/i }).first().click();

    const processBtn = page.getByRole("button", { name: /^Process$/i });
    if (await processBtn.isVisible()) {
      await processBtn.click();
    }

    await expect(page.getByText(/ready/i).first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/ai-generated transcript/i).first()).toBeVisible();
    await expect(page.getByText(/original recording|review important words/i).first()).toBeVisible();
  });

  test("Upload and process Video evidence, verify video audio transcript rendering", async ({ page }) => {
    test.setTimeout(60000);
    await registerAndLoginUser(page);

    await page.goto("/evidence");
    await page.locator("#upload-evidence-btn").click();

    await page.getByLabel(/title/i).first().fill("Unboxing Proof Video");
    const videoPath = path.resolve("e2e/fixtures/sample_video.mp4");
    await page.setInputFiles("input[type=file]", videoPath);
    await page.getByRole("button", { name: /upload file/i }).click();

    await expect(page.getByText(/unboxing proof video/i).first()).toBeVisible({ timeout: 10000 });
    await page.getByRole("button", { name: /unboxing proof video/i }).first().click();

    const processBtn = page.getByRole("button", { name: /^Process$/i });
    if (await processBtn.isVisible()) {
      await processBtn.click();
    }

    await expect(page.getByText(/ready/i).first()).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/ai-generated transcript/i).first()).toBeVisible();
  });
});
