import { test, expect } from "@playwright/test";

test.describe("Pipeline Control", () => {
  test("should have start button visible", async ({ page }) => {
    await page.goto("/");
    const startBtn = page.locator("#btn-start");
    await expect(startBtn).toBeVisible();
  });

  test("should have stop button visible", async ({ page }) => {
    await page.goto("/");
    const stopBtn = page.locator("#btn-stop");
    await expect(stopBtn).toBeVisible();
  });

  test("should allow changing chunk duration", async ({ page }) => {
    await page.goto("/");
    const input = page.locator("#input-chunk-duration");
    await expect(input).toBeVisible();
    await input.fill("10");
    await expect(input).toHaveValue("10");
  });
});