import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { createUser, fulfillReply, randomUser, signInAndOnboard, type TestUser } from "./helpers";

async function noSeriousAxe(page: Page, name: string) {
  let results;
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      results = await new AxeBuilder({ page }).analyze();
      break;
    } catch {
      if (attempt === 1) throw Error(`axe failed on ${name}`);
      await page.waitForLoadState("networkidle");
    }
  }
  const serious = results!.violations.filter((v) => v.impact === "serious");
  const critical = results!.violations.filter((v) => v.impact === "critical");
  expect(critical, `critical on ${name}`).toEqual([]);
  expect(serious, `serious on ${name}`).toEqual([]);
}

test("learn screen creates a session and sends a message to the real tutor", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything…").waitFor({ state: "visible", timeout: 20_000 });

  // send a message
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain Python functions");
  await page.getByRole("button", { name: "Send" }).click();

  // an AI reply (aria) appears
  await expect(page.locator(".msg-aria .mh-name").first()).toBeVisible({ timeout: 30_000 });
  await noSeriousAxe(page, "learn");
});

test("selecting a session whose messages fail does not leave the page stuck loading", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/learn");
  const input = page.getByPlaceholder("Ask ARIA anything…");
  await input.waitFor({ state: "visible", timeout: 20_000 });

  // Sessions are created on the first message, so hold two conversations.
  // Chats are listed by topic, not by the question's wording.
  for (const [question, topic] of [["Explain Python functions", /Python Functions/i], ["What is a loop?", /Loop/i]] as const) {
    await input.fill(question);
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page.locator(".session-item .session-title", { hasText: topic })).toBeVisible({ timeout: 60_000 });
    await page.getByRole("button", { name: "New chat" }).click();
  }
  await expect(page.locator(".session-item")).toHaveCount(2, { timeout: 20_000 });

  // Fail only message-list GETs; the POST (send) and session-list calls must still succeed.
  await page.route("**/api/v1/study/sessions/*/messages", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"boom"}' });
      return;
    }
    await route.continue();
  });

  // Click the older session — the bug left the page on "Loading your tutor..." forever.
  const other = page.locator(".session-item").nth(1);
  await other.waitFor({ state: "visible", timeout: 20_000 });
  await other.click();

  // The full-page loading spinner must clear (no stuck state) and a toast must appear.
  await expect(page.getByText("Loading your tutor").first()).toBeHidden({ timeout: 20_000 });
  await expect(page.getByText("Could not load this session.").first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByPlaceholder("Ask ARIA anything…")).toBeVisible({ timeout: 20_000 });

  await page.unroute("**/api/v1/study/sessions/*/messages");
  await noSeriousAxe(page, "learn-failed-session");
});

test("empty learn screen renders starter prompt chips and clicking one sends the prompt", async ({ page }) => {
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything…").waitFor({ state: "visible", timeout: 20_000 });

  // Starter chip is visible
  const chip = page.getByRole("button", { name: /Explain a hard idea to me simply/i });
  await expect(chip).toBeVisible({ timeout: 10_000 });
  await chip.click();

  // Sending starts and reply appears
  await expect(page.locator(".msg-aria .mh-name").first()).toBeVisible({ timeout: 30_000 });
});


test("returning to Learn opens a fresh chat and lists the old one by topic", async ({ page }) => {
  test.setTimeout(150_000);
  const user: TestUser = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);

  await page.goto("/app/learn");
  const input = page.getByPlaceholder("Ask ARIA anything…");
  await input.waitFor({ state: "visible", timeout: 20_000 });
  await input.fill("Explain Python functions");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.locator(".msg-aria").first()).toBeVisible({ timeout: 60_000 });
  await expect(page).toHaveURL(/[?&]session=/);

  // Leave via the workspace rail, then come back through navigation.
  await page.getByRole("navigation", { name: "Workspace" }).getByRole("link", { name: "Home", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  await page.getByRole("navigation", { name: "Workspace" }).getByRole("link", { name: "Learn", exact: true }).click();

  await expect(page.locator(".chat-body .msg")).toHaveCount(0, { timeout: 20_000 });
  await expect(page).not.toHaveURL(/[?&]session=/);
  const previous = page.locator(".session-item", { hasText: /Python Functions/i });
  await expect(previous).toBeVisible({ timeout: 20_000 });
  await expect(previous.locator(".session-title")).toContainText(/Python Functions/i);

  // Re-opening it from history restores the conversation.
  await previous.click();
  await expect(page.locator(".chat-body .msg-aria").first()).toBeVisible({ timeout: 20_000 });
});

test("a long answer becomes study cards: next, dots, a flip card and full text", async ({ page }) => {
  test.setTimeout(120_000);
  const user = randomUser();
  await createUser(user);
  await signInAndOnboard(page, user);
  const reply = [
    "Dynamic programming reuses answers to smaller problems.",
    "### What is dynamic programming", "Solving each sub-problem once and storing it.",
    "### How memoization works", "Cache each result the first time it is computed.",
    "### Example: Fibonacci", "```python\nfib = [0, 1]\n```",
    "### Key takeaways", "- Overlapping sub-problems\n- Optimal substructure",
    "### Check yourself", "What two properties does a problem need?", "Answer: Overlapping sub-problems and optimal substructure.",
  ].join("\n\n");
  await page.route("**/api/v1/study/sessions/*/messages/stream", (route) => fulfillReply(route, { id: "r1", role: "assistant", content: reply, depth: "deep", sources: [] }));
  await page.goto("/app/learn");
  await page.getByPlaceholder("Ask ARIA anything…").fill("Explain dynamic programming");
  await page.getByRole("button", { name: "Send", exact: true }).click();

  await expect(page.locator(".study-deck-count")).toHaveText("1 / 5 · swipe for more, tap to open", { timeout: 20_000 });
  await expect(page.locator(".flip-card")).toHaveCount(5);
  await expect(page.locator(".flip-card").first().locator(".front .study-card-kind")).toContainText("Definition");
  const quiz = page.locator(".flip-card.kind-quiz");
  await expect(quiz.locator(".front")).toContainText("What two properties");
  await quiz.click();
  await expect(quiz).toHaveAttribute("aria-pressed", "true");
  await expect(quiz.locator(".back")).toContainText("Overlapping sub-problems and optimal substructure");
  await page.getByRole("button", { name: "Full text", exact: true }).click();
  await expect(page.locator(".msg-aria .reply-block")).toHaveCount(5);
});
