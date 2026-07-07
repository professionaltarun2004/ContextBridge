/**
 * Claude Domain-Isolated Content Scraper
 * Target: claude.ai
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

const PLATFORM = "claude" as const;

const SELECTORS = {
  /** Individual conversation turn containers */
  HUMAN_TURN: "[data-testid='human-turn'], .human-turn",
  ASSISTANT_TURN: "[data-testid='ai-turn'], .assistant-turn",
  /** All turn containers — Claude uses a grid-based layout */
  ALL_TURNS: ".conversation-content [class*='grid'], [data-testid*='turn']",
  /** Inner prose/code content */
  CONTENT_PROSE: ".prose, [class*='whitespace-pre-wrap'], p, pre",
  /** Conversation scroll root */
  CONVERSATION_ROOT: "[data-testid='conversation-content'], main",
} as const;

/**
 * Pure DOM parsing function for Claude.ai conversation threads.
 * Claude renders turns inside alternating divs identified by data-testid.
 */
export function parseClaudeDOM(root: Element): RawMessagePayload {
  const messages: Message[] = [];

  // Claude wraps human and AI turns in separate identifiable containers
  const humanTurns = Array.from(
    root.querySelectorAll(SELECTORS.HUMAN_TURN)
  );
  const assistantTurns = Array.from(
    root.querySelectorAll(SELECTORS.ASSISTANT_TURN)
  );

  // Interleave human and assistant turns in order
  const maxLen = Math.max(humanTurns.length, assistantTurns.length);

  if (maxLen === 0) {
    throw new Error(
      "Claude: No conversation turns found. DOM selector may have changed."
    );
  }

  for (let i = 0; i < maxLen; i++) {
    const humanEl = humanTurns[i];
    if (humanEl !== undefined) {
      const text = extractTextContent(humanEl);
      if (text.length > 0) {
        messages.push(buildMessage("user", text));
      }
    }

    const assistantEl = assistantTurns[i];
    if (assistantEl !== undefined) {
      const text = extractTextContent(assistantEl);
      if (text.length > 0) {
        messages.push(buildMessage("assistant", text));
      }
    }
  }

  return { sourcePlatform: PLATFORM, messages };
}

/**
 * Extracts meaningful text content from a turn container.
 * Prefers prose containers; falls back to full textContent.
 */
function extractTextContent(element: Element): string {
  const proseEl = element.querySelector(SELECTORS.CONTENT_PROSE);
  if (proseEl !== null) {
    return proseEl.textContent?.trim() ?? "";
  }
  return element.textContent?.trim() ?? "";
}

async function initClaudeScraper(): Promise<void> {
  const run = async (): Promise<void> => {
    try {
      const state = await readState();
      const payload = parseClaudeDOM(document.body);
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

void initClaudeScraper();
