/**
 * ContextBridge API Client
 * Handles all TLS-encrypted communications with the FastAPI backend.
 * Appends JWT tokens from chrome.storage.local to all authenticated requests.
 * Implements offline fallback when the backend is unreachable.
 */

import type {
  SanitizedMessagePayload,
  SyncResponse,
  MatchContextResponse,
  ParseError,
} from "../types/index";
import { readState, writeState } from "./storage";

const API_BASE_URL = "https://api.contextbridge.ai/api/v1";

interface ApiClientOptions {
  timeoutMs?: number;
}

/**
 * Makes an authenticated fetch request to the backend.
 * Attaches the JWT from local storage and handles timeout/offline scenarios.
 */
async function authenticatedFetch<T>(
  path: string,
  init: RequestInit,
  options: ApiClientOptions = {}
): Promise<T> {
  const { timeoutMs = 5000 } = options;
  const state = await readState();

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    "x-request-id": crypto.randomUUID(),
    ...init.headers,
  };

  if (state.jwtToken !== null) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${state.jwtToken}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return (await response.json()) as T;
  } catch (err) {
    clearTimeout(timeoutId);
    // Mark as offline — extension will use local storage fallback
    await writeState({ offlineMode: true });
    throw err;
  }
}

/**
 * Syncs a sanitized payload to the backend.
 * POST /api/v1/sync — Returns a generated summary + conversation ID.
 * FR-005, FR-003
 */
export async function syncPayload(
  payload: SanitizedMessagePayload
): Promise<SyncResponse> {
  const body = {
    sourcePlatform: payload.sourcePlatform,
    messages: payload.messages,
  };

  const response = await authenticatedFetch<SyncResponse>("/sync", {
    method: "POST",
    body: JSON.stringify(body),
  });

  await writeState({ offlineMode: false, lastSyncAt: new Date().toISOString() });
  return response;
}

/**
 * Fetches the top semantic context matches for a given query.
 * GET /api/v1/context — Used to hydrate the extension with historical context.
 * FR-005
 */
export async function fetchContext(
  query: string
): Promise<MatchContextResponse> {
  const url = `/context?q=${encodeURIComponent(query)}`;
  return authenticatedFetch<MatchContextResponse>(url, { method: "GET" });
}

/**
 * Reports a DOM parser error to the backend telemetry endpoint.
 * POST /api/v1/telemetry/scraper-error — Optional authentication.
 * NFR-003
 */
export async function reportScraperError(error: ParseError): Promise<void> {
  const state = await readState();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "x-request-id": crypto.randomUUID(),
  };

  if (state.jwtToken !== null) {
    headers["Authorization"] = `Bearer ${state.jwtToken}`;
  }

  try {
    await fetch(`${API_BASE_URL}/telemetry/scraper-error`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        platform: error.sourcePlatform,
        targetURL: error.targetURL,
        errorLog: error.errorMessage,
        domStructureSnippet: error.domStructureSnippet,
      }),
    });
  } catch {
    // Telemetry failures are non-fatal — suppress silently.
  }
}
