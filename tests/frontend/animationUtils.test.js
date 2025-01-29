/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from "vitest";
import { initializeAnimation, updateAnimationVisibility } from "../../web/static/js/animationUtils.js";

// Mock `loadDotLottie` function
vi.mock("../../web/static/js/animationUtils.js", async () => {
  const originalModule = await vi.importActual("../../web/static/js/animationUtils.js");
  return {
    ...originalModule,
    loadDotLottie: vi.fn(async (src) => {
      if (src.startsWith("https:")) {
        console.error("Mocked: External URL access is not allowed in tests");
        throw new Error("Mocked URL loading error");
      }
      return {
        play: vi.fn(),
        stop: vi.fn(),
      };
    }),
  };
});

describe("initializeAnimation", () => {
  it("should initialize a Lottie animation correctly", async () => {
    // Set up the DOM environment
    document.body.innerHTML = '<canvas id="test-animation"></canvas>';

    // Run the function
    await initializeAnimation("test-animation", "https://lottie.host/example-animation.lottie");

    // Verify results
    const canvas = document.getElementById("test-animation");
    expect(canvas).not.toBeNull();
    expect(canvas.width).toBe(300); // Replace with actual expected width
    expect(canvas.height).toBe(300); // Replace with actual expected height
  });

  it("should log an error if canvas is not found", async () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    // Call with a non-existent canvas ID
    await initializeAnimation("non-existent-canvas", "https://lottie.host/example-animation.lottie");

    // Verify the error log
    expect(consoleSpy).toHaveBeenCalledWith("Canvas with ID non-existent-canvas not found.");
    consoleSpy.mockRestore();
  });

  it("should handle initialization errors gracefully", async () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    // Set up the DOM environment
    document.body.innerHTML = '<canvas id="test-animation"></canvas>';

    // Mock `loadDotLottie` to throw an error
    const { loadDotLottie } = await import("../../web/static/js/animationUtils.js");
    loadDotLottie.mockImplementationOnce(async () => {
      throw new Error("Initialization error");
    });

    // Run the function
    await initializeAnimation("test-animation", "https://lottie.host/example-animation.lottie");

    // Verify the error handling
    expect(consoleSpy).toHaveBeenCalledWith(
      "Failed to initialize animation for test-animation:",
      expect.any(Error)
    );
    consoleSpy.mockRestore();
  });
});

describe("updateAnimationVisibility", () => {
  it("should update visibility of animations", () => {
    // Set up the DOM environment
    document.body.innerHTML = `
      <canvas id="animation1" class="animation visible"></canvas>
      <canvas id="animation2" class="animation hidden"></canvas>
    `;

    const animationSteps = {
      1: "animation1",
      2: "animation2",
    };

    // Run the function to update visibility
    updateAnimationVisibility(2, animationSteps);

    // Verify visibility updates
    const animation1 = document.getElementById("animation1");
    const animation2 = document.getElementById("animation2");

    expect(animation1.classList.contains("hidden")).toBe(true);
    expect(animation2.classList.contains("visible")).toBe(true);
  });
});
