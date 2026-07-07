/**
 * Gemini Domain-Isolated Content Scraper
 * Target: gemini.google.com
 *
 * FR-001, AC4: Domain-isolated; no shared namespace with other scrapers.
 */

import type { Message, RawMessagePayload } from "../types/index";
import {
  buildMessage,
  buildParseError,
  observeWithDebounce,
} from "./base";
import { sanitizePayload } from "../utils/sanitizer";
import { readState, appendParseError } from "../utils/storage";

const PLATFORM = "gemini" as const;

const SELECTORS = {
  /** Gemini uses model-response and user-query containers */
  USER_QUERY: "user-query, [class*='user-query']",
  MODEL_RESPONSE: "model-response, [class*='model-response']",
  /** Query text within user-query */
  QUERY_TEXT: ".query-text, p, [class*='text']",
  /** Response markdown within model-response */
  RESPONSE_TEXT: "message-content, .response-container, p, [class*='markdown']",
  /** Conversation scroll root */
  CONVERSATION_ROOT:
    "chat-history, [class*='chat-history'], conversation-container",
} as const;

/**
 * Pure DOM parsing function for Gemini conversation threads.
 * Gemini renders custom web components (user-query, model-response).
 */
export function parseGeminiDOM(root: Element): RawMessagePayload {
  const messages: Message[] = [];

  const userQueries = Array.from(root.querySelectorAll(SELECTORS.USER_QUERY));
  const modelResponses = Array.from(
    root.querySelectorAll(SELECTORS.MODEL_RESPONSE)
  );

  const maxLen = Math.max(userQueries.length, modelResponses.length);

  if (maxLen === 0) {
    throw new Error(
      "Gemini: No conversation turns found. DOM selector may have changed."
    );
  }

  for (let i = 0; i < maxLen; i++) {
    const userEl = userQueries[i];
    if (userEl !== undefined) {
      const textEl = userEl.querySelector(SELECTORS.QUERY_TEXT);
      const text = (textEl ?? userEl).textContent?.trim() ?? "";
      if (text.length > 0) {
        messages.push(buildMessage("user", text));
      }
    }

    const modelEl = modelResponses[i];
    if (modelEl !== undefined) {
      const textEl = modelEl.querySelector(SELECTORS.RESPONSE_TEXT);
      const text = (textEl ?? modelEl).textContent?.trim() ?? "";
      if (text.length > 0) {
        messages.push(buildMessage("assistant", text));
      }
    }
  }

  return { sourcePlatform: PLATFORM, messages };
}

async function initGeminiScraper(): Promise<void> {
  const run = async (): Promise<void> => {
    try {
      const state = await readState();
      const payload = parseGeminiDOM(document.body);
      const sanitized = await sanitizePayload(payload, state.blocklist);

      chrome.runtime.sendMessage({
        type: "SCRAPE_RESULT",
        payload: sanitized,
      });
    } catch (err) {
      const errorData = buildParseError(PLATFORM, err, document.body);
      await appendParseError(errorData);
      chrome.runtime.sendMessage({ type: "PARSE_ERROR", error: errorData });
    }
  };

  await run();

  const root =
    document.querySelector(SELECTORS.CONVERSATION_ROOT) ?? document.body;

  observeWithDebounce(root, () => {
    void run();
  });
}

void initGeminiScraper();
