import { defineConfig } from "vitest/config";

export default defineConfig({
    test: {
        environment: "jsdom", // Use jsdom for DOM-related tests
        setupFiles: ["vitest.setup.js"], // Include setup file for mocking `canvas`
        include: ["web/tests/**/*.test.js"], // Ensure test files are included
        globals: true,
    },
});
