import { expect, test } from "@playwright/test";
import { authedApi, createUser, randomUser, signInAndOnboard, type TestUser } from "./helpers";

test.describe("Learning Agent Features & Screenshots", () => {
  test.setTimeout(120_000);

  test("1. Captures screenshot of Learn screen empty state with starter recommendation chips", async ({ page }, testInfo) => {
    const user: TestUser = randomUser();
    await createUser(user);
    await signInAndOnboard(page, user);

    await page.goto("/app/learn");
    await page.getByPlaceholder("Ask ARIA anything…").waitFor({ state: "visible", timeout: 20_000 });

    // Verify starter chips are rendered
    await expect(page.getByRole("button", { name: /Explain the core concepts/i })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: /Give me a practical, real-world example/i })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: /Quiz me on key concepts/i })).toBeVisible({ timeout: 10_000 });

    // Verify voice microphone button is enabled and ready
    const micBtn = page.getByRole("button", { name: "Speak question" });
    await expect(micBtn).toBeVisible();
    await expect(micBtn).toBeEnabled();

    // Capture screenshot of the starter chips UI
    await page.screenshot({
      path: testInfo.outputPath("learn_starter_chips.png"),
      fullPage: true,
    });
  });

  test("2. Conversational chat without uploaded documents captures rich answer and source footer", async ({ page }, testInfo) => {
    const user: TestUser = randomUser();
    await createUser(user);
    await signInAndOnboard(page, user);

    await page.goto("/app/learn");
    await page.getByPlaceholder("Ask ARIA anything…").waitFor({ state: "visible", timeout: 20_000 });

    // Wait for the starter chip to become enabled (context loaded)
    const chip = page.getByRole("button", { name: /Explain the core concepts/i });
    await expect(chip).toBeEnabled({ timeout: 15_000 });
    await chip.click();

    // Wait for the AI Tutor reply
    await expect(page.getByText("ARIA Tutor").first()).toBeVisible({ timeout: 60_000 });
    await expect(page.locator(".msg-aria").first()).toBeVisible({ timeout: 60_000 });

    // Give time for layout and markdown to finish rendering
    await page.waitForTimeout(1500);

    // Capture screenshot of conversational chat
    await page.screenshot({
      path: testInfo.outputPath("learn_conversational_chat.png"),
      fullPage: true,
    });
  });

  test("3. Uploaded document produces structured dual-source response with document citations", async ({ page }, testInfo) => {
    const user: TestUser = randomUser();
    await createUser(user);
    await signInAndOnboard(page, user);

    // Seed a document into the active context
    const api = await authedApi(user);
    const ctxList = await api.get("/api/v1/contexts").then((r) => r.json());
    expect(ctxList.length).toBeGreaterThan(0);
    const contextId = ctxList[0].id;

    await api.post("/api/v1/resources/text", {
      data: {
        context_id: contextId,
        title: "Relational Database Normalization",
        text: "Normalization reduces data redundancy. 1NF requires atomic values. "
          + "2NF removes partial functional dependencies on candidate keys. "
          + "3NF removes transitive functional dependencies. BCNF is an advanced version of 3NF.",
      },
    });

    await page.goto("/app/learn");
    await page.getByPlaceholder("Ask ARIA anything…").waitFor({ state: "visible", timeout: 20_000 });

    // Ask a question about normalization
    await page.getByPlaceholder("Ask ARIA anything…").fill("What are 1NF, 2NF, and 3NF, and why are they important? Keep the breakdown crisp.");
    await page.getByRole("button", { name: "Send" }).click();

    // Wait for ARIA response with source citations
    await expect(page.getByText("ARIA Tutor").first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/Grounded in your material/i).first()).toBeVisible({ timeout: 60_000 });

    await page.waitForTimeout(2000);

    // Expand the scroll container so the element screenshot captures the entire bubble from top to bottom
    await page.evaluate(() => {
      const body = document.querySelector<HTMLElement>(".chat-body");
      if (body) {
        body.style.overflow = "visible";
        body.style.maxHeight = "none";
        body.style.height = "auto";
      }
      const shell = document.querySelector<HTMLElement>(".chat-shell");
      if (shell) {
        shell.style.overflow = "visible";
        shell.style.maxHeight = "none";
        shell.style.height = "auto";
      }
      const sidebarLayout = document.querySelector<HTMLElement>(".chat-sidebar-layout");
      if (sidebarLayout) {
        sidebarLayout.style.overflow = "visible";
        sidebarLayout.style.height = "auto";
      }
    });

    await page.waitForTimeout(500);

    const ariaMsg = page.locator(".msg-aria").last();
    await ariaMsg.scrollIntoViewIfNeeded();

    // Capture screenshot of the full dual-source grounded response element
    await ariaMsg.screenshot({
      path: testInfo.outputPath("learn_dual_source_grounding.png"),
    });

    await api.dispose();
  });

  test("4. Voice microphone records speech and populates chat input via transcription API", async ({ page }) => {
    const user: TestUser = randomUser();
    await createUser(user);
    await signInAndOnboard(page, user);

    // Mock the /api/v1/audio/transcribe response
    await page.route("**/api/v1/audio/transcribe", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ text: "What is concurrency in Go?" }),
      });
    });

    // Mock navigator.mediaDevices.getUserMedia and MediaRecorder in the browser context
    await page.addInitScript(() => {
      class MockMediaRecorder extends EventTarget {
        state = "inactive";
        mimeType = "audio/webm";
        ondataavailable: ((e: Pick<BlobEvent, "data">) => void) | null = null;
        onstop: (() => void) | null = null;

        static isTypeSupported() {
          return true;
        }

        start() {
          this.state = "recording";
        }

        stop() {
          this.state = "inactive";
          if (this.ondataavailable) {
            this.ondataavailable({ data: new Blob(["mock-audio-data"], { type: "audio/webm" }) });
          }
          if (this.onstop) {
            this.onstop();
          }
        }
      }

      Object.defineProperty(window, "MediaRecorder", { value: MockMediaRecorder, configurable: true });

      if (!navigator.mediaDevices) {
        Object.defineProperty(navigator, "mediaDevices", { value: {}, configurable: true });
      }
      navigator.mediaDevices.getUserMedia = async () => {
        return {
          getTracks: () => [{ stop: () => {} }],
        } as unknown as MediaStream;
      };
    });

    await page.goto("/app/learn");
    await page.getByPlaceholder("Ask ARIA anything…").waitFor({ state: "visible", timeout: 20_000 });

    const micBtn = page.getByRole("button", { name: "Speak question" });
    await expect(micBtn).toBeVisible();
    await expect(micBtn).toBeEnabled();

    // Click to start recording
    await micBtn.click();

    // Verify recording state: button label changes to "Stop recording voice"
    await expect(page.getByRole("button", { name: "Stop recording voice" })).toBeVisible({ timeout: 5000 });

    // Click again to stop recording and trigger transcription
    await page.getByRole("button", { name: "Stop recording voice" }).click();

    // Transcribed text should be inserted into the input field!
    const input = page.getByPlaceholder("Ask ARIA anything…");
    await expect(input).toHaveValue("What is concurrency in Go?", { timeout: 10_000 });

    // Toast confirmation should be visible
    await expect(page.getByText("Voice transcribed!")).toBeVisible({ timeout: 10_000 });
  });
});
