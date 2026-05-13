import { test, expect } from "@playwright/test";

test.describe("Pipeline Control", () => {
  test("should have start button visible", async ({ page }) => {
    await page.goto("/");
    const startBtn = page.locator("[data-testid='btn-start']");
    await expect(startBtn).toBeVisible();
  });

  test("should have stop button visible", async ({ page }) => {
    await page.goto("/");
    const stopBtn = page.locator("[data-testid='btn-stop']");
    await expect(stopBtn).toBeVisible();
  });

  test("should change chunk duration", async ({ page }) => {
    await page.goto("/");
    const input = page.locator("[data-testid='chunk-duration-input']");
    await input.fill("10");
    const confirmBtn = page.locator("[data-testid='btn-apply-chunk']");
    await confirmBtn.click();
  });

  test("should show preset dropdown", async ({ page }) => {
    await page.goto("/");
    const presetSelect = page.locator("[data-testid='preset-select']");
    await expect(presetSelect).toBeVisible();
  });
});
