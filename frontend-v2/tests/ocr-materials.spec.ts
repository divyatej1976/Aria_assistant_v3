import path from "path";
import { expect, test } from "@playwright/test";
import { createUser, randomUser, signInAndOnboard, type TestUser } from "./helpers";

const ARTIFACT_DIR = "C:/Users/Divya Tejaswi/.gemini/antigravity/brain/56fcb0a1-3f52-45ed-9524-e296604eaf6d";
const SCREENSHOT_DIR = path.resolve(__dirname, "../../screenshots");
const PUBLIC_SCREENSHOT_DIR = path.resolve(__dirname, "../public/screenshots");

test.describe("OCR Document & Image Ingestion", () => {
  test.setTimeout(120_000);

  test("1. Materials library supports OCR image upload and creates an IMAGE resource", async ({ page }) => {
    const user: TestUser = randomUser();
    await createUser(user);
    await signInAndOnboard(page, user);

    await page.goto("/app/materials");
    await page.getByRole("heading", { name: "Library", exact: true }).waitFor({ state: "visible", timeout: 20_000 });

    // Open Add resource modal
    await page.getByRole("button", { name: "Add resource" }).first().click();

    // Verify OCR file upload tab is selected by default
    await expect(page.getByText("Upload file (PDF / Image OCR)")).toBeVisible();

    // Set file input
    const imagePath = path.resolve(__dirname, "../test-assets/sample_ocr_notes.png");
    await page.locator("#resource-file").setInputFiles(imagePath);

    // Click Add resource inside modal
    await page.locator(".modal").getByRole("button", { name: "Add resource" }).click();

    // Wait for the modal to close and the new resource card to render
    await expect(page.getByText("sample_ocr_notes").first()).toBeVisible({ timeout: 25_000 });
    await expect(page.getByText(/IMAGE/i).first()).toBeVisible({ timeout: 25_000 });
    await expect(page.getByText(/READY/i).first()).toBeVisible({ timeout: 25_000 });

    await page.waitForTimeout(1000);

    // Capture screenshot of Materials library with the OCR resource
    await page.screenshot({
      path: `${ARTIFACT_DIR}/materials_ocr_resource.png`,
      fullPage: true,
    });
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "materials_ocr_resource.png"),
      fullPage: true,
    });
    await page.screenshot({
      path: path.join(PUBLIC_SCREENSHOT_DIR, "materials_ocr_resource.png"),
      fullPage: true,
    });
  });

  test("2. Learning agent allows in-chat image attachment and answers grounded in OCR text", async ({ page }) => {
    const user: TestUser = randomUser();
    await createUser(user);
    await signInAndOnboard(page, user);

    await page.goto("/app/learn");
    await page.getByPlaceholder("Ask ARIA anything…").waitFor({ state: "visible", timeout: 20_000 });

    // Attach image via in-chat file input
    const imagePath = path.resolve(__dirname, "../test-assets/sample_ocr_notes.png");
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(imagePath);

    // The file waits in the input bar until the question is sent
    await expect(page.locator(".pending-file").filter({ hasText: "sample_ocr_notes" })).toBeVisible();

    // Ask ARIA a question about the attached image notes
    await page.getByPlaceholder("Ask ARIA anything…").fill(
      "Based on my attached notes, what are the three properties in the CAP Theorem and what does each guarantee?"
    );
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page.locator(".msg-file").filter({ hasText: "sample_ocr_notes" })).toBeVisible();

    // Wait for ARIA response with dual-source grounding
    await expect(page.locator(".msg-aria .mh-name").first()).toBeVisible({ timeout: 60_000 });
    await expect(page.locator(".msg-aria .source-chip").first()).toBeVisible({ timeout: 60_000 });

    await page.waitForTimeout(2000);

    // Expand containers for clean, full capture
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

    // Capture screenshot of the full dual-source OCR-grounded response
    await ariaMsg.screenshot({
      path: `${ARTIFACT_DIR}/learn_ocr_in_chat_attachment.png`,
    });
    await ariaMsg.screenshot({
      path: path.join(SCREENSHOT_DIR, "learn_ocr_in_chat_attachment.png"),
    });
    await ariaMsg.screenshot({
      path: path.join(PUBLIC_SCREENSHOT_DIR, "learn_ocr_in_chat_attachment.png"),
    });
  });
});
