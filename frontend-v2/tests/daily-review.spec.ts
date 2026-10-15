import { expect, test } from "@playwright/test";
import { activeContextId, authedApi, createUser, randomUser, seedResource, signInAndOnboard, answerQuiz } from "./helpers";

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
    await page.getByPlaceholder("Ask ARIA anything…").fill("Explain Python functions and how arguments and return values work");
    await page.getByRole("button", { name: "Send", exact: true }).click();
    await expect(page.locator("article.msg-aria").first()).toBeVisible({ timeout: 60_000 });
    const finished = await api.post(`/api/v1/study/contexts/${contextId}/finish-day`);
    expect(finished.ok(), await finished.text()).toBe(true);
    const id = ((await finished.json()) as { assessment_id: string }).assessment_id;
    // Finishing twice the same day returns the same review.
    const again = await api.post(`/api/v1/study/contexts/${contextId}/finish-day`);
    expect(((await again.json()) as { assessment_id: string }).assessment_id).toBe(id);
    await page.goto(`/app/assess?review=${id}`);
    const card = page.locator(`#review-${id}`);
    await expect(card).toBeVisible();
    await expect(card).toBeFocused();
    await page.reload();
    await expect(card).toBeVisible();
    await card.click();
    await answerQuiz(page);
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
