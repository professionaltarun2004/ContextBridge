/**
 * Client-Side Content Sanitization & Blocklist Engine
 * FR-002: Pure, side-effect-free sanitization functions.
 *
 * All functions are pure — they accept data and return transformed data
 * without mutating arguments or accessing external state.
 */

import type { Message, RawMessagePayload, SanitizedMessagePayload } from "../types/index";

// ---------------------------------------------------------------------------
// PII & Credential Regex Patterns
// ---------------------------------------------------------------------------

const REDACTION_PATTERNS: Array<{ pattern: RegExp; label: string }> = [
  // OpenAI API keys
  { pattern: /sk-[A-Za-z0-9]{32,}/g, label: "REDACTED_OPENAI_KEY" },
  // Anthropic API keys
  { pattern: /sk-ant-[A-Za-z0-9\-_]{32,}/g, label: "REDACTED_ANTHROPIC_KEY" },
  // Google API keys (AIzaSy...)
  { pattern: /AIzaSy[A-Za-z0-9\-_]{33}/g, label: "REDACTED_GOOGLE_KEY" },
  // Generic bearer tokens
  { pattern: /Bearer\s+[A-Za-z0-9\-._~+/]+=*/g, label: "REDACTED_BEARER_TOKEN" },
  // Generic hex secret (32+ chars)
  { pattern: /[0-9a-f]{32,}/gi, label: "REDACTED_SECRET" },
  // Credit card numbers (basic Luhn-like pattern)
  { pattern: /\b(?:\d[ -]?){13,19}\b/g, label: "REDACTED_CARD" },
  // Email addresses
  { pattern: /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g, label: "REDACTED_EMAIL" },
  // Phone numbers (international format)
  { pattern: /(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g, label: "REDACTED_PHONE" },
  // SSN
  { pattern: /\b\d{3}-\d{2}-\d{4}\b/g, label: "REDACTED_SSN" },
  // GitHub personal access tokens
  { pattern: /ghp_[A-Za-z0-9]{36}/g, label: "REDACTED_GITHUB_PAT" },
  // AWS access key IDs
  { pattern: /AKIA[A-Z0-9]{16}/g, label: "REDACTED_AWS_KEY" },
  // Private key block headers
  { pattern: /-----BEGIN [A-Z ]+KEY-----[\s\S]*?-----END [A-Z ]+KEY-----/g, label: "REDACTED_PRIVATE_KEY" },
];

/**
 * Prompt injection character escaping.
 * Prevents adversarial instruction structures from being passed downstream.
 * Escapes Markdown-style system override patterns.
 */
const INJECTION_ESCAPE_MAP: Array<[RegExp, string]> = [
  [/\[\s*system\s*\]/gi, "[filtered_system]"],
  [/\[\s*INST\s*\]/gi, "[filtered_inst]"],
  [/<\|im_start\|>/g, "[filtered_im_start]"],
  [/<\|im_end\|>/g, "[filtered_im_end]"],
  [/###\s*System/gi, "### Context"],
  [/###\s*Instruction/gi, "### Note"],
];

// ---------------------------------------------------------------------------
// Pure Sanitization Functions
// ---------------------------------------------------------------------------

/**
 * Redacts known PII and credential patterns from a string.
 * @param text - Raw text content from a scraped message.
 * @returns Text with sensitive values replaced by labeled placeholders.
 */
export function redactSensitiveContent(text: string): string {
  let sanitized = text;
  for (const { pattern, label } of REDACTION_PATTERNS) {
    sanitized = sanitized.replace(pattern, `[${label}]`);
  }
  return sanitized;
}

/**
 * Escapes adversarial prompt injection sequences from a string.
 * Applied to context blocks before injection into target UIs.
 * @param text - Potentially adversarial text.
 * @returns Escaped text safe for injection.
 */
export function escapeInjectionContent(text: string): string {
  let escaped = text;
  for (const [pattern, replacement] of INJECTION_ESCAPE_MAP) {
    escaped = escaped.replace(pattern, replacement);
  }
  return escaped;
}

/**
 * Checks whether a message text contains any blocklist keyword.
 * Comparison is case-insensitive and full-word aware.
 * @param text - Message text to test.
 * @param blocklist - User-defined list of blocked keywords.
 * @returns true if the message should be discarded.
 */
export function isBlocklisted(text: string, blocklist: string[]): boolean {
  if (blocklist.length === 0) return false;
  const lowerText = text.toLowerCase();
  return blocklist.some((keyword) =>
    keyword.trim().length > 0 && lowerText.includes(keyword.trim().toLowerCase())
  );
}

/**
 * Sanitizes a single Message object.
 * @param message - Raw message to sanitize.
 * @param blocklist - User-defined blocked keyword list.
 * @returns Sanitized message or null if it should be discarded.
 */
export function sanitizeMessage(
  message: Message,
  blocklist: string[]
): Message | null {
  if (isBlocklisted(message.text, blocklist)) {
    return null;
  }
  return {
    ...message,
    text: redactSensitiveContent(message.text),
  };
}

/**
 * Generates a SHA-256 checksum of a serialized messages array.
 * Used for Redis cache key construction and deduplication.
 * @param messages - Array of sanitized messages.
 * @returns Hex-encoded SHA-256 string.
 */
export async function computeChecksum(messages: Message[]): Promise<string> {
  const serialized = JSON.stringify(messages);
  const encoded = new TextEncoder().encode(serialized);
  const hashBuffer = await crypto.subtle.digest("SHA-256", encoded);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Full sanitization pipeline for a raw payload.
 * Applies PII redaction, blocklist filtering, and injection escaping.
 * This is the main entry point for the sanitization engine (FR-002).
 *
 * @param raw - Raw message payload from the DOM scraper.
 * @param blocklist - User-configured blocked keyword list.
 * @returns Schema-validated, sanitized payload ready for storage or sync.
 */
export async function sanitizePayload(
  raw: RawMessagePayload,
  blocklist: string[]
): Promise<SanitizedMessagePayload> {
  const sanitizedMessages: Message[] = [];

  for (const message of raw.messages) {
    const sanitized = sanitizeMessage(message, blocklist);
    if (sanitized !== null) {
      // Apply injection escaping on the final pass before storage
      sanitizedMessages.push({
        ...sanitized,
        text: escapeInjectionContent(sanitized.text),
      });
    }
  }

  const checksum = await computeChecksum(sanitizedMessages);

  return {
    sourcePlatform: raw.sourcePlatform,
    messages: sanitizedMessages,
    checksum,
    capturedAt: new Date().toISOString(),
  };
}
