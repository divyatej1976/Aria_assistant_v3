import { expect, test } from "@playwright/test";
import {
  authedApi,
  createUser,
  randomUser,
  seedResource,
  signInAndOnboard,
} from "./helpers";

/**
 * Regression: the backend persists tutor messages with role="assistant";
 * the Learn page must render them as ARIA bubbles after a reload, not as
 * user bubbles (which is what happened before the role normalization).
 */
test("tutor replies render as ARIA bubbles after a page reload", async ({ page }) => {
  test.setTimeout(180_000);
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  const contextId = await (await import("./helpers")).activeContextId(page);
  const api = await authedApi(user);
  await seedResource(api, contextId);

  await page.goto("/app/learn");
  const input = page.getByPlaceholder("Ask ARIA anything…");
  await input.waitFor({ state: "visible", timeout: 20_000 });
  await input.fill("Explain Python functions");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.locator(".msg-aria").first()).toBeVisible({ timeout: 60_000 });

  await page.reload();
  await expect(
    page.locator(".chat-body .msg-aria").first(),
    "reloaded tutor reply must render as an ARIA bubble",
  ).toBeVisible({ timeout: 30_000 });
  await api.dispose();
});
