/**
 * Base scraper utilities shared across all domain-specific content scripts.
 * All functions here are pure and side-effect-free.
 */

import type { Message, MessageRole, ParseError, SourcePlatform } from "../types/index";

/**
 * Extracts a compact DOM structure snippet for diagnostic telemetry.
 * Captures tag names, class lists, and IDs of the top-level children.
 */
export function extractDomSnippet(root: Element): string {
  const children = Array.from(root.children).slice(0, 5);
  return children
    .map((el) => {
      const tag = el.tagName.toLowerCase();
      const id = el.id ? `#${el.id}` : "";
      const classes = Array.from(el.classList)
        .slice(0, 3)
        .map((c) => `.${c}`)
        .join("");
      return `<${tag}${id}${classes}>`;
    })
    .join(" | ");
}

/**
 * Builds a ParseError diagnostic object when a selector fails.
 */
export function buildParseError(
  platform: SourcePlatform,
  err: unknown,
  root: Element | null
): ParseError {
  const message = err instanceof Error ? err.message : String(err);
  const snippet = root !== null ? extractDomSnippet(root) : "no-root-element";

  return {
    sourcePlatform: platform,
    targetURL: window.location.href,
    errorMessage: message,
    domStructureSnippet: snippet,
    timestamp: new Date().toISOString(),
  };
}

/**
 * Normalizes a role string from a target DOM attribute into a typed MessageRole.
 * Returns "assistant" as the default for unrecognized values.
 */
export function normalizeRole(raw: string): MessageRole {
  const lower = raw.toLowerCase().trim();
  if (lower === "user" || lower === "human") return "user";
  if (lower === "system") return "system";
  return "assistant";
}

/**
 * Creates a Message object from extracted text and role data.
 * Ensures all messages have a timestamp even if DOM doesn't provide one.
 */
export function buildMessage(
  role: MessageRole,
  text: string,
  timestamp?: string
): Message {
  return {
    role,
    text: text.trim(),
    timestamp: timestamp ?? new Date().toISOString(),
  };
}

/**
 * Sets up a MutationObserver on a target element.
 * Debounces the callback to prevent redundant parses during streaming responses.
 * Returns the observer for cleanup.
 */
export function observeWithDebounce(
  target: Element,
  callback: () => void,
  debounceMs = 800
): MutationObserver {
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  const observer = new MutationObserver(() => {
    if (debounceTimer !== null) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(callback, debounceMs);
  });

  observer.observe(target, {
    childList: true,
    subtree: true,
    characterData: true,
  });

  return observer;
}
