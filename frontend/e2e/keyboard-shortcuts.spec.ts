import { test, expect } from "@playwright/test";

test.describe("Keyboard Shortcuts", () => {
  test("should toggle log panel with Ctrl+L", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Control+l");
    await expect(page.locator("[data-testid='log-panel']")).toBeVisible();
  });

  test("should open help modal with ? button", async ({ page }) => {
    await page.goto("/");
    const helpBtn = page.locator("[data-testid='btn-shortcuts-help']");
    if (await helpBtn.isVisible()) {
      await helpBtn.click();
      await expect(page.locator("[data-testid='shortcuts-modal']")).toBeVisible();
    }
  });

  test("should close modal with Escape", async ({ page }) => {
    await page.goto("/");
    const helpBtn = page.locator("[data-testid='btn-shortcuts-help']");
    if (await helpBtn.isVisible()) {
      await helpBtn.click();
      await page.keyboard.press("Escape");
      await expect(page.locator("[data-testid='shortcuts-modal']")).toBeHidden();
    }
  });
});
