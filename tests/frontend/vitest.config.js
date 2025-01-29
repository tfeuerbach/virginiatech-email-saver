export default defineConfig({
    test: {
        environment: "jsdom",
        setupFiles: ["tests/frontend/vitest.setup.js"],
        include: ["tests/**/*.test.js"],
        globals: true,
    },
});
