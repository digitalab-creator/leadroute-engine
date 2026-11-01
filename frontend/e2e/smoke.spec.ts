import { expect, test } from "@playwright/test";

test.describe("operator smoke", () => {
  test("health and queue load seed leads", async ({ page }) => {
    const health = await page.request.get("/health");
    expect(health.ok()).toBeTruthy();
    expect(await health.json()).toMatchObject({ status: "ok" });

    await page.goto("/");
    await expect(page.getByText("LeadRoute")).toBeVisible();
    await expect(page.getByRole("button", { name: "Add a message" })).toBeEnabled({
      timeout: 15_000,
    });
    await expect(page.locator('a.card[href^="/leads/"]').first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test("KPI pack shows the reporting week and acquisition tiles", async ({ page }) => {
    await page.goto("/kpi");
    await expect(page.getByRole("heading", { name: "KPI pack" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText("Qualified leads")).toBeVisible();
    await expect(page.getByText("By first-touch source")).toBeVisible();
  });

  test("AI visibility shows gaps and the top brief", async ({ page }) => {
    await page.goto("/visibility");
    await expect(page.getByRole("heading", { name: "AI visibility" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("heading", { name: "Brief for the top gap" })).toBeVisible();
  });

  test("lead detail opens from the queue", async ({ page }) => {
    await page.goto("/");
    const firstLead = page.locator('a.card[href^="/leads/"]').first();
    await expect(firstLead).toBeVisible({ timeout: 15_000 });
    const href = await firstLead.getAttribute("href");
    expect(href).toMatch(/^\/leads\//);
    await firstLead.click();
    await expect(page).toHaveURL(href ?? "");
    await expect(page.getByRole("button", { name: "Accept" })).toBeVisible({
      timeout: 15_000,
    });
  });
});
