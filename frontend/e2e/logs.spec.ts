import { test, expect } from "@playwright/test";

test.describe("Log Panel", () => {
  test("should toggle log panel visibility", async ({ page }) => {
    await page.goto("/");
    const toggle = page.locator("[data-testid='btn-toggle-logs']");
    await toggle.click();
    await expect(page.locator("#log-content")).toBeVisible();
    await toggle.click();
    await expect(page.locator("#log-content")).toBeHidden();
  });

  test("should show log entries", async ({ page }) => {
    await page.goto("/");
    const toggle = page.locator("[data-testid='btn-toggle-logs']");
    await toggle.click();
    const entries = page.locator("[data-testid='log-entry']");
    await expect(entries.first()).toBeVisible({ timeout: 5000 });
  });

  test("should filter logs by level", async ({ page }) => {
    await page.goto("/");
    await page.locator("[data-testid='btn-toggle-logs']").click();
    const filter = page.locator("[data-testid='log-level-filter']");
    await filter.selectOption("ERROR");
    await page.waitForTimeout(300);
  });

  test("should export logs", async ({ page }) => {
    await page.goto("/");
    await page.locator("[data-testid='btn-toggle-logs']").click();
    await expect(page.locator("[data-testid='log-entry']").first()).toBeVisible(
      {
        timeout: 10000,
      },
    );
    const exportBtn = page.locator("[data-testid='btn-export-logs']").first();
    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 10000 }),
      exportBtn.click(),
    ]);
    expect(download.suggestedFilename()).toContain("srt2web-logs");
  });
});
