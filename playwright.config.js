const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests",
  timeout: 90000,
  workers: 1,
  reporter: "list",
  use: {
    headless: true,
    viewport: { width: 1440, height: 900 },
    screenshot: "only-on-failure"
  }
});