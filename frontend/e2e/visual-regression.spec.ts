/**
 * Visual Regression Tests
 *
 * Takes screenshots of key dashboard states and compares them.
 * Run: npx playwright test --config=frontend/playwright.config.ts
 *
 * For first run: npx playwright test --update-snapshots
 */

import { test, expect } from "@playwright/test";

test.describe("Visual Regression", () => {
  test("dashboard renders without crash", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".dashboard", { timeout: 10000 });
    await expect(page).toHaveScreenshot("dashboard-initial.png", {
      maxDiffPixelRatio: 0.05,
    });
  });

  test("header displays correctly", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".header", { timeout: 10000 });
    await expect(page.locator(".header")).toHaveScreenshot("header.png", {
      maxDiffPixelRatio: 0.05,
    });
  });

  test("status card shows stopped state", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".status-card", { timeout: 10000 });
    await expect(page.locator(".status-card")).toHaveScreenshot(
      "status-card-stopped.png",
      { maxDiffPixelRatio: 0.05 }
    );
  });

  test("metrics card renders bars", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".metrics-card", { timeout: 10000 });
    await expect(page.locator(".metrics-card")).toHaveScreenshot(
      "metrics-card.png",
      { maxDiffPixelRatio: 0.05 }
    );
  });

  test("process grid displays all modules", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".process-grid", { timeout: 10000 });
    await expect(page.locator(".process-grid")).toHaveScreenshot(
      "process-grid.png",
      { maxDiffPixelRatio: 0.05 }
    );
  });

  test("log panel collapsed state", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".log-panel", { timeout: 10000 });
    await expect(page.locator(".log-panel")).toHaveScreenshot(
      "logpanel-collapsed.png",
      { maxDiffPixelRatio: 0.05 }
    );
  });

  test("dark theme toggle", async ({ page }) => {
    await page.goto("/");
    await page.waitForSelector(".btn-theme", { timeout: 10000 });
    await page.locator(".btn-theme").click();
    await expect(page.locator("html")).not.toHaveClass("dark");
    await expect(page.locator(".dashboard")).toHaveScreenshot(
      "dashboard-light.png",
      { maxDiffPixelRatio: 0.05 }
    );
  });
});
