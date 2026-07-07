/**
 * Chrome Storage Utility
 * Provides typed read/write helpers for chrome.storage.local.
 * All sensitive state (JWT, blocklist, payload) lives exclusively here — NFR-004.
 */

import type { StorageState } from "../types/index";

const STORAGE_KEY = "contextbridge_state";

const DEFAULT_STATE: StorageState = {
  activePayload: null,
  blocklist: [],
  jwtToken: null,
  lastSyncAt: null,
  parseErrors: [],
  offlineMode: false,
};

/**
 * Reads the full extension state from chrome.storage.local.
 * Returns a merged default if no state has been persisted yet.
 */
export async function readState(): Promise<StorageState> {
  return new Promise((resolve) => {
    chrome.storage.local.get(STORAGE_KEY, (result) => {
      const stored = result[STORAGE_KEY] as Partial<StorageState> | undefined;
      resolve({ ...DEFAULT_STATE, ...stored });
    });
  });
}

/**
 * Writes a partial state update to chrome.storage.local.
 * Merges with the existing state rather than overwriting.
 */
export async function writeState(
  update: Partial<StorageState>
): Promise<void> {
  const current = await readState();
  const next: StorageState = { ...current, ...update };
  return new Promise((resolve) => {
    chrome.storage.local.set({ [STORAGE_KEY]: next }, resolve);
  });
}

/**
 * Clears all stored extension state.
 * Used during logout or full reset operations.
 */
export async function clearState(): Promise<void> {
  return new Promise((resolve) => {
    chrome.storage.local.remove(STORAGE_KEY, resolve);
  });
}

/**
 * Appends a parse error to the local error cache for Sentry telemetry.
 * Limited to the last 50 errors to prevent unbounded growth.
 */
export async function appendParseError(
  error: StorageState["parseErrors"][number]
): Promise<void> {
  const current = await readState();
  const errors = [...current.parseErrors, error].slice(-50);
  await writeState({ parseErrors: errors });
}
