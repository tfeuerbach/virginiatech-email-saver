/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from "vitest";

// Mock `@lottiefiles/dotlottie-web`
vi.mock("@lottiefiles/dotlottie-web", () => ({
  DotLottie: vi.fn().mockImplementation(() => ({
    play: vi.fn(),
    stop: vi.fn(),
  })),
}));

describe("animations", () => {
  it("should handle form submission", () => {
    document.body.innerHTML = `
      <form id="credentials-form">
        <input type="email" id="vt_email" value="test@vt.edu" />
        <input type="password" id="vt_password" value="password123" />
      </form>
    `;

    const form = document.getElementById("credentials-form");
    expect(form).not.toBeNull();

    form.dispatchEvent(new Event("submit"));
    // Assertions based on the expected behavior
  });
});
