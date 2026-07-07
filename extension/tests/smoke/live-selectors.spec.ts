/**
 * T16 (scaffold): Live smoke tests against real LLM interfaces.
 * These tests verify that DOM selectors are still valid on target platforms.
 * Run on a 6h GHA cron schedule (NFR-003).
 */

import { test, expect } from "@playwright/test";

const TARGETS = [
  {
    name: "ChatGPT",
    url: "https://chatgpt.com",
    promptSelector: "#prompt-textarea",
    messageSelector: "[data-testid^='conversation-turn-']",
  },
  {
    name: "Claude",
    url: "https://claude.ai",
    promptSelector: ".ProseMirror[contenteditable='true']",
    messageSelector: "[data-testid='human-turn'], [data-testid='ai-turn']",
  },
  {
    name: "Gemini",
    url: "https://gemini.google.com",
    promptSelector: "rich-textarea .ql-editor",
    messageSelector: "user-query, model-response",
  },
] as const;

for (const target of TARGETS) {
  test(`${target.name}: Prompt input selector is present`, async ({ page }) => {
    await page.goto(target.url, { waitUntil: "networkidle", timeout: 20_000 });

    // Check for prompt textarea presence
    const promptEl = page.locator(target.promptSelector).first();
    await expect(promptEl).toBeVisible({ timeout: 10_000 });
  });
}
