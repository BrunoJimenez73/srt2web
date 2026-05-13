import { test, expect } from "@playwright/test";

test.describe("Dashboard", () => {
  test("should load and show header", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("header")).toBeVisible();
    await expect(page.locator("text=SRT2Web")).toBeVisible();
  });

  test("should show status card with pipeline state", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("[data-testid='status-card']")).toBeVisible();
  });

  test("should show metrics card", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("[data-testid='metrics-card']")).toBeVisible();
  });

  test("should show process grid with module cards", async ({ page }) => {
    await page.goto("/");
    const cards = page.locator("[data-testid='module-card']");
    await expect(cards.first()).toBeVisible();
  });

  test("should change input type and update form", async ({ page }) => {
    await page.goto("/");
    const select = page.locator("[data-testid='input-type-select']");
    await select.selectOption("file");
    await expect(page.locator("[data-testid='file-path-input']")).toBeVisible();
  });
});
