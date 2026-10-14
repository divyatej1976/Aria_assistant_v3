import { expect, test } from "@playwright/test";

/**
 * Auth-link flows: the emailed pages must CONSUME their token by calling the
 * corresponding confirmation endpoint, surface API errors inline, and keep
 * the resend fallback working. Backend happy-paths are covered by pytest;
 * here we verify the frontend wiring via network interception.
 */

test("verify-email consumes the token and shows success", async ({ page }) => {
  await page.route("**/api/v1/auth/verify-email/confirm", async (route) => {
    const body = route.request().postDataJSON() as { email: string; token: string };
    expect(body.email).toBe("user@example.com");
    expect(body.token).toBe("tok-abc");
    await route.fulfill({ status: 200, contentType: "application/json", body: '{"detail":"Email verified"}' });
  });

  await page.goto("/verify-email?email=user@example.com&token=tok-abc");

  await expect(page.getByText("Your email address is confirmed.")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("link", { name: /Continue to Sign In/i })).toBeVisible();
});

test("verify-email shows an inline error for an invalid token", async ({ page }) => {
  await page.route("**/api/v1/auth/verify-email/confirm", async (route) =>
    route.fulfill({ status: 422, contentType: "application/json", body: '{"detail":"Invalid or expired token"}' }),
  );

  await page.goto("/verify-email?email=user@example.com&token=bad");
  await expect(page.getByText(/invalid or expired/i).first()).toBeVisible({ timeout: 20_000 });
  // resend fallback stays available
  await page.route("**/api/v1/auth/verify-email/request", async (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: '{"detail":"sent"}' }),
  );
  await page.getByRole("button", { name: /Re-send verification email/i }).click();
});

test("reset-password consumes the token and sets a new password", async ({ page }) => {
  await page.route("**/api/v1/auth/password-reset/confirm", async (route) => {
    const body = route.request().postDataJSON() as {
      email: string;
      token: string;
      new_password: string;
    };
    expect(body.email).toBe("user@example.com");
    expect(body.token).toBe("tok-xyz");
    expect(body.new_password.length).toBeGreaterThanOrEqual(8);
    await route.fulfill({ status: 200, contentType: "application/json", body: '{"detail":"Password updated"}' });
  });

  await page.goto("/reset-password?email=user@example.com&token=tok-xyz");
  await page.getByLabel("New password", { exact: true }).fill("brand-new-pw-123");
  await page.getByLabel("Confirm new password").fill("brand-new-pw-123");
  await page.getByRole("button", { name: /Update password/i }).click();

  await expect(page.getByText(/Password updated/i).first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("link", { name: /Continue to Sign In/i })).toBeVisible();
});

test("reset-password surfaces an inline error for an expired link", async ({ page }) => {
  await page.route("**/api/v1/auth/password-reset/confirm", async (route) =>
    route.fulfill({ status: 422, contentType: "application/json", body: '{"detail":"Invalid or expired reset link"}' }),
  );

  await page.goto("/reset-password?email=user@example.com&token=expired");
  await page.getByLabel("New password", { exact: true }).fill("brand-new-pw-123");
  await page.getByLabel("Confirm new password").fill("brand-new-pw-123");
  await page.getByRole("button", { name: /Update password/i }).click();

  await expect(page.getByText(/invalid or expired/i).first()).toBeVisible({ timeout: 20_000 });
});
