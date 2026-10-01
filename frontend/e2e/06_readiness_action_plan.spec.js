import { test, expect } from "@playwright/test";
import { registerAndLoginUser } from "./helpers/test-utils.js";

test.describe("Case Readiness and Action Planner E2E Suite", () => {
  test("Open Case Readiness and Action Plan modals, verify grounded information", async ({ page }) => {
    test.setTimeout(90000);
    await registerAndLoginUser(page);

    await page.goto("/chat");
    const newChatBtn = page.getByRole("button", { name: /(\+ New legal chat|Start a legal chat)/i }).first();
    await newChatBtn.click();
    const titleInput = page.getByLabel(/chat title/i);
    await expect(titleInput).toBeVisible();
    await titleInput.fill("Readiness & Plan Workspace");
    await page.getByRole("button", { name: /create chat/i }).click();

    const composer = page.getByLabel(/ask a legal-information question/i);
    await composer.fill("I bought a defective product on 10 Jan 2026 for Rs 50,000 and the seller refuses to refund under Consumer Protection Act.");
    await page.getByRole("button", { name: /send/i }).click();
    await expect(page.getByText(/\[SOURCE_1\]/i)).toBeVisible({ timeout: 50000 });

    // Open Case Readiness Modal
    const readinessBtn = page.getByRole("button", { name: /case readiness/i });
    if (!await readinessBtn.isVisible()) {
      await page.getByRole("button", { name: /actions/i }).click();
    }
    await page.getByRole("button", { name: /case readiness/i }).click();

    const readinessDialog = page.getByRole("dialog");
    await expect(readinessDialog).toBeVisible();
    await expect(readinessDialog.getByRole("heading", { name: /case readiness/i })).toBeVisible();
    await expect(readinessDialog.getByText(/facts established/i)).toBeVisible({ timeout: 10000 });

    await page.keyboard.press("Escape");
    await expect(readinessDialog).not.toBeVisible();

    // Open Action Plan Modal
    const actionPlanBtn = page.getByRole("button", { name: /action plan/i });
    if (!await actionPlanBtn.isVisible()) {
      await page.getByRole("button", { name: /actions/i }).click();
    }
    await page.getByRole("button", { name: /action plan/i }).click();

    const planDialog = page.getByRole("dialog");
    await expect(planDialog).toBeVisible();
    await expect(planDialog.getByRole("heading", { name: /action plan/i })).toBeVisible({ timeout: 10000 });
    await expect(planDialog.getByText(/primary next step/i)).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(planDialog).not.toBeVisible();
  });
});
