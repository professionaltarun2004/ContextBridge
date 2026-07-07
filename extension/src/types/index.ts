/**
 * Shared type definitions for ContextBridge extension.
 * All modules import from this file to ensure schema consistency.
 */

export type MessageRole = "user" | "assistant" | "system";

export type SourcePlatform = "chatgpt" | "claude" | "gemini" | "local";

export interface Message {
  role: MessageRole;
  text: string;
  timestamp: string;
}

export interface RawMessagePayload {
  sourcePlatform: SourcePlatform;
  messages: Message[];
}

export interface SanitizedMessagePayload {
  sourcePlatform: SourcePlatform;
  messages: Message[];
  /** SHA-256 checksum of the serialized messages array for deduplication */
  checksum: string;
  capturedAt: string;
}

export interface ParseError {
  sourcePlatform: SourcePlatform;
  targetURL: string;
  errorMessage: string;
  domStructureSnippet: string;
  timestamp: string;
}

export interface StorageState {
  activePayload: SanitizedMessagePayload | null;
  blocklist: string[];
  jwtToken: string | null;
  lastSyncAt: string | null;
  parseErrors: ParseError[];
  offlineMode: boolean;
}

export interface SyncRequest {
  sourcePlatform: string;
  messages: Array<{
    role: string;
    text: string;
    timestamp: string;
  }>;
}

export interface SyncResponse {
  conversationId: string;
  summaryText: string;
  presetApplied: string;
}

export interface ContextMatch {
  chunkId: string;
  summaryText: string;
  similarityScore: number;
}

export interface MatchContextResponse {
  matches: ContextMatch[];
}

// Messages passed between content scripts and background worker
export type ExtensionMessage =
  | { type: "SCRAPE_RESULT"; payload: RawMessagePayload }
  | { type: "PARSE_ERROR"; error: ParseError }
  | { type: "GET_STATE"; requestId: string }
  | { type: "STATE_RESPONSE"; state: StorageState; requestId: string }
  | { type: "INJECT_CONTEXT"; summary: string }
  | { type: "CONTEXT_AVAILABLE"; summary: string }
  | { type: "SYNC_NOW" }
  | { type: "EXPORT_REQUESTED"; format: "json" | "markdown" }
  | { type: "IMPORT_PAYLOAD"; raw: string };
