import { test, expect } from "@playwright/test";

test.describe("Dashboard", () => {
  test("should load and show header", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("header")).toBeVisible();
    await expect(page.locator("header")).toContainText("SRT2Web");
  });

  test("should show status card with pipeline state", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#status-card")).toBeVisible();
  });

  test("should show metrics card", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#metrics-card")).toBeVisible();
  });

  test("should show process grid with module cards", async ({ page }) => {
    await page.goto("/");
    const cards = page.locator(".module-card");
    await expect(cards.first()).toBeVisible();
  });

  test("should change input type and update form", async ({ page }) => {
    await page.goto("/");
    const select = page.locator("#input-type");
    await select.selectOption("file");
    await expect(page.locator("#input-file-path")).toBeVisible();
  });
});
