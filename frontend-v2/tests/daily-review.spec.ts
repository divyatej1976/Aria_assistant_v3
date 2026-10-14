import { expect, test } from "@playwright/test";
import { activeContextId, authedApi, createUser, randomUser, seedResource, signInAndOnboard } from "./helpers";

test("finish the day saves a review and preserves compact square activity cells", async ({ page }) => {
  test.setTimeout(180_000);
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  const contextId = await activeContextId(page);
  const api = await authedApi(user);
  try {
    await seedResource(api, contextId);
    await page.goto("/app/learn");
    await page.getByPlaceholder("Ask ARIA anything...").fill("Explain Python functions and how arguments and return values work");
    await page.getByRole("button", { name: "Send", exact: true }).click();
    const finish = page.getByRole("button", { name: "Done for today", exact: true });
    await expect(finish).toBeEnabled({ timeout: 60_000 });
    await finish.click();
    const link = page.getByRole("link", { name: "Start review" });
    await expect(link).toBeVisible({ timeout: 60_000 });
    const href = await link.getAttribute("href");
    await finish.click();
    await expect(link).toHaveAttribute("href", href!);
    await link.click();
    const id = new URL(href!, "http://localhost").searchParams.get("review")!;
    const card = page.locator(`#review-${id}`);
    await expect(card).toBeVisible();
    await expect(card).toBeFocused();
    await page.reload();
    await expect(card).toBeVisible();
    await card.click();
    const radios = page.locator('input[type="radio"]');
    await expect(radios.first()).toBeVisible();
    const names = await radios.evaluateAll(inputs => [...new Set(inputs.map(input => (input as HTMLInputElement).name))]);
    for (const name of names) await page.locator(`input[type="radio"][name="${name}"]`).first().check();
    await page.getByRole("button", { name: /Submit Answers/i }).click();
    await expect(page.getByRole("heading", { name: "Answer Review", exact: true })).toBeVisible();
    await page.goto("/app/progress");
    const cell = page.locator(".heat .cell").first();
    await expect(cell).toBeVisible();
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: 900 });
      await cell.hover();
      const box = await cell.boundingBox();
      expect(box?.width).toBe(13);
      expect(box?.height).toBe(13);
    }
  } finally {
    await api.dispose();
  }
});
