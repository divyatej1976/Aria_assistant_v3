import { expect, test } from "@playwright/test";
import { activeContextId, authedApi, createUser, randomUser, signInAndOnboard } from "./helpers";

test("LangGraph chat action creates audio and survives reload", async ({ page }, testInfo) => {
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain stacks briefly.");
  await page.getByRole("button", {name: "Send", exact: true}).click();
  await expect(page.locator("article.msg-aria").first()).toBeVisible({timeout: 60000});
  await page.getByPlaceholder("Ask ARIA anything…").fill("Make audio from this chat");
  await page.getByRole("button", {name: "Send", exact: true}).click();
  const card = page.getByRole("region", {name: "Conversation audio action"});
  await expect(card).toHaveAttribute("data-action-status", "done", {timeout: 120000});
  await page.screenshot({path: testInfo.outputPath("chat-action-done.png")});
  await page.reload();
  await expect(card.getByRole("link", {name: "Listen in Audio"})).toBeVisible();
  const link = await card.getByRole("link", {name: "Listen in Audio"}).getAttribute("href");
  await card.getByRole("link", {name: "Listen in Audio"}).click();
  await expect(page.locator(link!.slice(link!.indexOf("#")))) .toBeVisible();
  const api = await authedApi(user);
  const listed = await api.get(`/api/v1/audio?context_id=${await activeContextId(page)}`);
  expect((await listed.json()).length).toBe(1);
  await api.dispose();
});

test("lost run response is recovered without a second episode", async ({ page }) => {
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain queues briefly.");
  await page.getByRole("button", {name: "Send", exact: true}).click();
  await expect(page.locator("article.msg-aria").first()).toBeVisible({timeout: 60000});
  let runs = 0;
  await page.route("**/orchestration/actions/*/run", async route => {
    runs++;
    await route.fetch();
    await route.abort(); // execution finished, but the browser loses the response
  });
  await page.getByPlaceholder("Ask ARIA anything…").fill("Make audio from this chat");
  await page.getByRole("button", {name: "Send", exact: true}).click();
  const card = page.getByRole("region", {name: "Conversation audio action"});
  await expect(card).toHaveAttribute("data-action-status", "done", {timeout: 120000});
  await page.reload();
  await expect(card).toHaveAttribute("data-action-status", "done");
  expect(runs).toBe(1);
  const api = await authedApi(user);
  const listed = await api.get(`/api/v1/audio?context_id=${await activeContextId(page)}`);
  expect((await listed.json()).length).toBe(1);
  await api.dispose();
});

test("failed card can retry and keeps the same episode", async ({ page }) => {
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain lists briefly.");
  await page.getByRole("button", {name: "Send", exact: true}).click();
  await expect(page.locator("article.msg-aria").first()).toBeVisible({timeout: 60000});
  let runs = 0;
  await page.route("**/orchestration/actions/*/run", async route => {
    const response = await route.fetch();
    const body = await response.json();
    runs++;
    // Simulate a stale failed response after an earlier successful publication.
    await route.fulfill({response, json: runs === 1 ? {...body, status: "failed", message: "Audio could not be created. Please retry."} : body});
  });
  await page.getByPlaceholder("Ask ARIA anything…").fill("Make audio from this chat");
  await page.getByRole("button", {name: "Send", exact: true}).click();
  const card = page.getByRole("region", {name: "Conversation audio action"});
  await expect(card.getByRole("button", {name: "Retry audio"})).toBeVisible({timeout: 120000});
  await card.getByRole("button", {name: "Retry audio"}).click();
  await expect(card).toHaveAttribute("data-action-status", "done");
  const api = await authedApi(user);
  const listed = await api.get(`/api/v1/audio?context_id=${await activeContextId(page)}`);
  expect((await listed.json()).length).toBe(1);
  await api.dispose();
});
