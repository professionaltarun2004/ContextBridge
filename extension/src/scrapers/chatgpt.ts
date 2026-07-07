/**
 * ChatGPT Domain-Isolated Content Scraper
 * Target: chatgpt.com / chat.openai.com
 *
 * This module is injected exclusively on ChatGPT pages. It runs a pure
 * DOM parsing function against conversation turn containers and reports
 * structured JSON to the background worker.
 *
 * FR-001, AC4: Domain-isolated; no shared namespace with other scrapers.
 */

import type { Message, RawMessagePayload } from "../types/index";
import {
  buildMessage,
  buildParseError,
  normalizeRole,
  observeWithDebounce,
} from "./base";
import { sanitizePayload } from "../utils/sanitizer";
import { readState, appendParseError } from "../utils/storage";

const PLATFORM = "chatgpt" as const;

/**
 * ChatGPT conversation turn selectors.
 * These are the primary DOM targets. If they change, the error is caught,
 * cached, and reported silently (FR-001, AC3).
 */
const SELECTORS = {
  /** Outer turn wrapper — contains data-testid="conversation-turn-N" */
  TURN_WRAPPER: "[data-testid^='conversation-turn-']",
  /** Role indicator — data-message-author-role attribute */
  AUTHOR_ROLE_ATTR: "data-message-author-role",
  /** Message content container */
  MESSAGE_CONTENT: "[data-message-content='true'], .markdown, .text-token-text-primary",
  /** Chat scroll container */
  CONVERSATION_ROOT: "main [class*='flex flex-col']",
} as const;

/**
 * Pure DOM parsing function for ChatGPT conversation threads.
 * Accepts a document root element and returns a structured message list.
 * No side effects — does not write to storage or call APIs.
 *
 * @param root - The document body or closest conversation container.
 * @returns Parsed RawMessagePayload or throws on selector mismatch.
 */
export function parseChatGPTDOM(root: Element): RawMessagePayload {
  const turnElements = root.querySelectorAll(SELECTORS.TURN_WRAPPER);

  if (turnElements.length === 0) {
    throw new Error(
      "ChatGPT: No conversation turns found. DOM selector may have changed."
    );
  }

  const messages: Message[] = [];

  for (const turn of Array.from(turnElements)) {
    const roleAttr =
      turn.getAttribute(SELECTORS.AUTHOR_ROLE_ATTR) ??
      turn.querySelector(`[${SELECTORS.AUTHOR_ROLE_ATTR}]`)?.getAttribute(
        SELECTORS.AUTHOR_ROLE_ATTR
      );

    if (roleAttr === null || roleAttr === undefined) continue;

    const contentEl = turn.querySelector(SELECTORS.MESSAGE_CONTENT);
    const text = contentEl?.textContent?.trim() ?? "";

    if (text.length === 0) continue;

    messages.push(buildMessage(normalizeRole(roleAttr), text));
  }

  return { sourcePlatform: PLATFORM, messages };
}

/**
 * Main entry point — sets up the MutationObserver and dispatches
 * scrape results to the background service worker.
 */
async function initChatGPTScraper(): Promise<void> {
  const run = async (): Promise<void> => {
    try {
      const state = await readState();
      const payload = parseChatGPTDOM(document.body);
      const sanitized = await sanitizePayload(payload, state.blocklist);

      chrome.runtime.sendMessage({
        type: "SCRAPE_RESULT",
        payload: sanitized,
      });
    } catch (err) {
      const errorData = buildParseError(PLATFORM, err, document.body);

      // AC3: Suppress UI errors; cache diagnostic for Sentry pipeline.
      await appendParseError(errorData);
      chrome.runtime.sendMessage({ type: "PARSE_ERROR", error: errorData });
    }
  };

  // Run once on load, then observe for changes
  await run();

  const root =
    document.querySelector(SELECTORS.CONVERSATION_ROOT) ?? document.body;

  observeWithDebounce(root, () => {
    void run();
  });
}

void initChatGPTScraper();
