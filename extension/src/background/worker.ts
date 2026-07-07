/**
 * ContextBridge Background Service Worker
 * Coordinates local data workflows, orchestrates sync with the backend,
 * and manages tab-change events.
 *
 * Runs as a Manifest V3 service worker — stateless across invocations.
 * All persistent state lives in chrome.storage.local.
 */

import type {
  ExtensionMessage,
  SanitizedMessagePayload,
} from "../types/index";
import { readState, writeState } from "../utils/storage";
import { syncPayload, fetchContext, reportScraperError } from "../utils/apiClient";

// ---------------------------------------------------------------------------
// Message Handler — dispatched from content scripts
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener(
  (message: ExtensionMessage, _sender, sendResponse) => {
    void handleMessage(message, sendResponse);
    // Return true to keep the message channel open for async responses
    return true;
  }
);

async function handleMessage(
  message: ExtensionMessage,
  sendResponse: (response?: unknown) => void
): Promise<void> {
  switch (message.type) {
    case "SCRAPE_RESULT":
      await handleScrapeResult(message.payload as SanitizedMessagePayload);
      sendResponse({ ok: true });
      break;

    case "PARSE_ERROR":
      // Forward error to backend telemetry (non-blocking)
      void reportScraperError(message.error);
      sendResponse({ ok: true });
      break;

    case "GET_STATE": {
      const state = await readState();
      const response: ExtensionMessage = {
        type: "STATE_RESPONSE",
        state,
        requestId: message.requestId,
      };
      sendResponse(response);
      break;
    }

    case "SYNC_NOW": {
      const state = await readState();
      if (state.activePayload !== null) {
        await triggerSync(state.activePayload);
      }
      sendResponse({ ok: true });
      break;
    }

    case "IMPORT_PAYLOAD": {
      await handleImport(message.raw);
      sendResponse({ ok: true });
      break;
    }

    default:
      sendResponse({ ok: false, error: "Unknown message type" });
  }
}

// ---------------------------------------------------------------------------
// Scrape Result Processing
// ---------------------------------------------------------------------------

async function handleScrapeResult(
  payload: SanitizedMessagePayload
): Promise<void> {
  const state = await readState();

  // Deduplication: skip if checksum matches the stored payload
  if (state.activePayload?.checksum === payload.checksum) {
    return;
  }

  await writeState({ activePayload: payload });

  // Attempt background sync if online and authenticated
  if (!state.offlineMode && state.jwtToken !== null) {
    void triggerSync(payload);
  }

  // Notify injectors on all supported tabs that context is available
  const summary = buildLocalSummary(payload);
  await broadcastContextAvailable(summary);
}

// ---------------------------------------------------------------------------
// Background Sync — FR-005
// ---------------------------------------------------------------------------

async function triggerSync(payload: SanitizedMessagePayload): Promise<void> {
  try {
    const response = await syncPayload(payload);
    // Broadcast the cloud-generated summary (more optimized than local)
    await broadcastContextAvailable(response.summaryText);
  } catch {
    // Offline fallback: use local summary derived from raw messages
    const summary = buildLocalSummary(payload);
    await broadcastContextAvailable(summary);
    await writeState({ offlineMode: true });
  }
}

// ---------------------------------------------------------------------------
// Context Hydration on Tab Switch — FR-004
// ---------------------------------------------------------------------------

chrome.tabs.onActivated.addListener(({ tabId }) => {
  void handleTabActivated(tabId);
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
  if (changeInfo.status === "complete") {
    void handleTabActivated(tabId);
  }
});

async function handleTabActivated(tabId: number): Promise<void> {
  const state = await readState();

  if (state.activePayload === null) {
    // Try fetching context from the backend if online
    if (!state.offlineMode && state.jwtToken !== null) {
      try {
        const result = await fetchContext("recent conversation");
        if (result.matches.length > 0) {
          const summary = result.matches[0]?.summaryText ?? "";
          if (summary.length > 0) {
            await notifyTab(tabId, summary);
          }
        }
      } catch {
        // Backend unreachable — stay in offline mode
      }
    }
    return;
  }

  const summary = buildLocalSummary(state.activePayload);
  await notifyTab(tabId, summary);
}

async function notifyTab(tabId: number, summary: string): Promise<void> {
  try {
    await chrome.tabs.sendMessage(tabId, {
      type: "CONTEXT_AVAILABLE",
      summary,
    } satisfies ExtensionMessage);
  } catch {
    // Tab may not have the injector loaded — suppress silently.
  }
}

async function broadcastContextAvailable(summary: string): Promise<void> {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  for (const tab of tabs) {
    if (tab.id !== undefined) {
      await notifyTab(tab.id, summary);
    }
  }
}

// ---------------------------------------------------------------------------
// Import Handler — FR-006
// ---------------------------------------------------------------------------

async function handleImport(raw: string): Promise<void> {
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!isValidPayload(parsed)) {
      throw new Error("Invalid payload schema");
    }
    await writeState({ activePayload: parsed });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Parse error";
    console.error("[ContextBridge Worker] Import failed:", message);
  }
}

/**
 * Runtime type guard for SanitizedMessagePayload.
 */
function isValidPayload(data: unknown): data is SanitizedMessagePayload {
  if (typeof data !== "object" || data === null) return false;
  const d = data as Record<string, unknown>;
  return (
    typeof d["sourcePlatform"] === "string" &&
    Array.isArray(d["messages"]) &&
    typeof d["checksum"] === "string" &&
    typeof d["capturedAt"] === "string"
  );
}

// ---------------------------------------------------------------------------
// Local Summary Builder — Offline Fallback
// ---------------------------------------------------------------------------

/**
 * Deterministic fallback summarizer: combines last 3 dialogue turns.
 * Used when the LiteLLM backend is unavailable (Solution: LiteLLM Timeout).
 */
function buildLocalSummary(payload: SanitizedMessagePayload): string {
  const lastThree = payload.messages.slice(-6);
  const lines = lastThree.map(
    (m) => `[${m.role.toUpperCase()}]: ${m.text.slice(0, 300)}`
  );
  return `[ContextBridge — ${payload.sourcePlatform.toUpperCase()} — Local Summary]\n\n${lines.join("\n\n")}`;
}

console.log("[ContextBridge] Background service worker initialized.");
