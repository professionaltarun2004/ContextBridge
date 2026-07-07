/**
 * Localhost Domain-Isolated Content Scraper
 * Target: http://localhost:*, http://127.0.0.1:*
 *
 * Targets local AI UI wrappers such as Ollama Web UI, LM Studio,
 * Open WebUI, and similar self-hosted frontends.
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

const PLATFORM = "local" as const;

/**
 * Multiple selector strategies for local UIs since they vary significantly.
 * Tried in order; first matching strategy wins.
 */
const STRATEGIES = [
  // Open WebUI / Ollama Web UI
  {
    turns: ".messages .message",
    roleAttr: "data-role",
    contentSelector: ".message-content, p",
  },
  // LM Studio
  {
    turns: "[class*='ChatMessage'], [class*='message-row']",
    roleAttr: "data-sender",
    contentSelector: "[class*='content'], p",
  },
  // Generic chat patterns
  {
    turns: "[class*='chat-message'], [class*='chat-turn']",
    roleAttr: "class",
    contentSelector: "p, div > span",
  },
] as const;

/**
 * Infers role from element class names when no explicit role attribute exists.
 * Looks for "user", "human", "assistant", "bot", "ai" substrings.
 */
function inferRoleFromClass(element: Element): "user" | "assistant" {
  const classList = Array.from(element.classList).join(" ").toLowerCase();
  if (
    classList.includes("user") ||
    classList.includes("human") ||
    classList.includes("you")
  ) {
    return "user";
  }
  return "assistant";
}

/**
 * Pure DOM parsing function for localhost AI UIs.
 * Tries multiple selector strategies to support various local UIs.
 */
export function parseLocalhostDOM(root: Element): RawMessagePayload {
  for (const strategy of STRATEGIES) {
    const turns = Array.from(root.querySelectorAll(strategy.turns));
    if (turns.length === 0) continue;

    const messages: Message[] = [];

    for (const turn of turns) {
      let role: "user" | "assistant" = "assistant";

      if (strategy.roleAttr === "class") {
        role = inferRoleFromClass(turn);
      } else {
        const rawRole = turn.getAttribute(strategy.roleAttr);
        if (rawRole !== null) {
          role = normalizeRole(rawRole) as "user" | "assistant";
        }
      }

      const contentEl = turn.querySelector(strategy.contentSelector);
      const text = (contentEl ?? turn).textContent?.trim() ?? "";

      if (text.length > 0) {
        messages.push(buildMessage(role, text));
      }
    }

    if (messages.length > 0) {
      return { sourcePlatform: PLATFORM, messages };
    }
  }

  throw new Error(
    "Localhost: No conversation turns matched any known strategy. " +
      "This may be an unsupported local AI UI."
  );
}

async function initLocalhostScraper(): Promise<void> {
  const run = async (): Promise<void> => {
    try {
      const state = await readState();
      const payload = parseLocalhostDOM(document.body);
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

  observeWithDebounce(document.body, () => {
    void run();
  });
}

void initLocalhostScraper();
