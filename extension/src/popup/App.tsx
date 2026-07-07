import React, { useState, useEffect, useCallback } from "react";
import type { StorageState, SanitizedMessagePayload } from "../types/index";

// ---------------------------------------------------------------------------
// Clipboard Utility — FR-006
// ---------------------------------------------------------------------------

function formatAsMarkdown(payload: SanitizedMessagePayload): string {
  const lines = [
    `# ContextBridge Export`,
    `**Platform:** ${payload.sourcePlatform}`,
    `**Captured:** ${payload.capturedAt}`,
    `**Checksum:** \`${payload.checksum.slice(0, 12)}...\``,
    ``,
    `## Conversation`,
    ``,
  ];

  for (const msg of payload.messages) {
    lines.push(`### ${msg.role.charAt(0).toUpperCase() + msg.role.slice(1)}`);
    lines.push(msg.text);
    lines.push(`*${msg.timestamp}*`);
    lines.push(``);
  }

  return lines.join("\n");
}

function formatAsJSON(payload: SanitizedMessagePayload): string {
  return JSON.stringify(payload, null, 2);
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type NotificationType = "success" | "error" | "warning";

interface Notification {
  type: NotificationType;
  message: string;
}

// ---------------------------------------------------------------------------
// App Component
// ---------------------------------------------------------------------------

export default function App(): React.ReactElement {
  const [state, setState] = useState<StorageState | null>(null);
  const [importText, setImportText] = useState("");
  const [blocklistOpen, setBlocklistOpen] = useState(false);
  const [newKeyword, setNewKeyword] = useState("");
  const [notification, setNotification] = useState<Notification | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);

  // Load state from chrome.storage.local on mount
  useEffect(() => {
    const loadState = (): void => {
      chrome.storage.local.get("contextbridge_state", (result) => {
        const stored = result["contextbridge_state"] as StorageState | undefined;
        if (stored !== undefined) {
          setState(stored);
        } else {
          setState({
            activePayload: null,
            blocklist: [],
            jwtToken: null,
            lastSyncAt: null,
            parseErrors: [],
            offlineMode: false,
          });
        }
      });
    };

    loadState();

    // Listen for storage changes
    const listener = (): void => loadState();
    chrome.storage.local.onChanged.addListener(listener);
    return () => chrome.storage.local.onChanged.removeListener(listener);
  }, []);

  const showNotification = useCallback(
    (type: NotificationType, message: string): void => {
      setNotification({ type, message });
      setTimeout(() => setNotification(null), 3000);
    },
    []
  );

  // ---------------------------------------------------------------------------
  // Export — FR-006, AC1 & AC2
  // ---------------------------------------------------------------------------

  const handleExport = async (format: "json" | "markdown"): Promise<void> => {
    if (state?.activePayload === null || state?.activePayload === undefined) {
      showNotification("warning", "No active context to export.");
      return;
    }

    const text =
      format === "json"
        ? formatAsJSON(state.activePayload)
        : formatAsMarkdown(state.activePayload);

    try {
      await navigator.clipboard.writeText(text);
      showNotification("success", `Copied as ${format.toUpperCase()} to clipboard!`);
    } catch {
      showNotification(
        "error",
        "Clipboard access denied. Please grant clipboard permissions."
      );
    }
  };

  // ---------------------------------------------------------------------------
  // Import — FR-006, AC3
  // ---------------------------------------------------------------------------

  const handleImport = (): void => {
    if (importText.trim().length === 0) {
      showNotification("warning", "Paste a JSON context block first.");
      return;
    }

    // Validate before sending to worker
    let parsed: unknown;
    try {
      parsed = JSON.parse(importText);
    } catch {
      showNotification("error", "Invalid JSON: could not parse the pasted text.");
      return;
    }

    const validationError = validateImportPayload(parsed);
    if (validationError !== null) {
      showNotification("error", `Schema validation failed: ${validationError}`);
      return;
    }

    chrome.runtime.sendMessage({
      type: "IMPORT_PAYLOAD",
      raw: importText,
    });

    setImportText("");
    showNotification("success", "Context imported successfully!");
  };

  // ---------------------------------------------------------------------------
  // Sync
  // ---------------------------------------------------------------------------

  const handleSync = async (): Promise<void> => {
    setIsSyncing(true);
    try {
      chrome.runtime.sendMessage({ type: "SYNC_NOW" });
      await new Promise((r) => setTimeout(r, 1500));
      showNotification("success", "Sync triggered!");
    } finally {
      setIsSyncing(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Blocklist — FR-002, AC3
  // ---------------------------------------------------------------------------

  const addKeyword = (): void => {
    const kw = newKeyword.trim();
    if (kw.length === 0) return;
    if (state?.blocklist.includes(kw)) {
      showNotification("warning", "Keyword already in blocklist.");
      return;
    }

    const updated = [...(state?.blocklist ?? []), kw];
    chrome.storage.local.get("contextbridge_state", (result) => {
      const stored = (result["contextbridge_state"] as StorageState) ?? {};
      chrome.storage.local.set({
        contextbridge_state: { ...stored, blocklist: updated },
      });
    });

    setNewKeyword("");
  };

  const removeKeyword = (keyword: string): void => {
    const updated = (state?.blocklist ?? []).filter((k) => k !== keyword);
    chrome.storage.local.get("contextbridge_state", (result) => {
      const stored = (result["contextbridge_state"] as StorageState) ?? {};
      chrome.storage.local.set({
        contextbridge_state: { ...stored, blocklist: updated },
      });
    });
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (state === null) {
    return (
      <div
        style={{
          padding: "32px",
          textAlign: "center",
          color: "var(--text-muted)",
        }}
      >
        Loading...
      </div>
    );
  }

  const { activePayload, offlineMode, lastSyncAt, blocklist } = state;

  const contextPreview =
    activePayload !== null
      ? activePayload.messages
          .slice(-4)
          .map((m) => `[${m.role}] ${m.text.slice(0, 100)}`)
          .join("\n")
      : null;

  return (
    <>
      {/* Header */}
      <div className="popup-header">
        <div className="popup-logo">
          <div className="popup-logo-icon">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.5"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h1>ContextBridge</h1>
        </div>
        <div className={`status-badge ${offlineMode ? "offline" : "online"}`}>
          <span className="status-dot" />
          {offlineMode ? "Offline" : "Online"}
        </div>
      </div>

      {/* Body */}
      <div className="popup-body">
        {/* Notification */}
        {notification !== null && (
          <div className={`notification ${notification.type}`}>
            <span>
              {notification.type === "success"
                ? "✓"
                : notification.type === "error"
                ? "✕"
                : "⚠"}
            </span>
            {notification.message}
          </div>
        )}

        {/* Context Card */}
        <div className="context-card">
          <div className="context-card-header">
            <span className="context-card-title">Active Context</span>
            {activePayload !== null && (
              <span className="platform-badge">
                {activePayload.sourcePlatform.toUpperCase()}
              </span>
            )}
          </div>

          {contextPreview !== null ? (
            <div className="context-preview">{contextPreview}</div>
          ) : (
            <div className="context-empty">
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <span>No context captured yet.</span>
              <span style={{ fontSize: "11px" }}>
                Open a supported AI chat page to begin.
              </span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="action-row">
          <button
            id="btn-export-json"
            className="btn btn-secondary btn-sm"
            onClick={() => void handleExport("json")}
            disabled={activePayload === null}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
            </svg>
            JSON
          </button>
          <button
            id="btn-export-md"
            className="btn btn-secondary btn-sm"
            onClick={() => void handleExport("markdown")}
            disabled={activePayload === null}
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
            </svg>
            Markdown
          </button>
          <button
            id="btn-sync"
            className="btn btn-primary btn-sm"
            onClick={() => void handleSync()}
            disabled={isSyncing || activePayload === null}
          >
            {isSyncing ? "Syncing…" : "↑ Sync"}
          </button>
        </div>

        {/* Import */}
        <div>
          <div className="section-label">Import Context</div>
          <div className="import-area">
            <textarea
              id="import-textarea"
              className="import-textarea"
              placeholder="Paste JSON context block here…"
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
            />
            <div className="import-footer">
              <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>
                Paste a previously exported context
              </span>
              <button
                id="btn-import"
                className="btn btn-primary btn-sm"
                onClick={handleImport}
              >
                Import
              </button>
            </div>
          </div>
        </div>

        {/* Blocklist */}
        <div className="blocklist-section">
          <div
            className="blocklist-header"
            onClick={() => setBlocklistOpen((o) => !o)}
          >
            <span className="blocklist-title">
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
              </svg>
              Keyword Blocklist
              <span className="blocklist-count">{blocklist.length}</span>
            </span>
            <svg
              className={`chevron ${blocklistOpen ? "open" : ""}`}
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>

          {blocklistOpen && (
            <div className="blocklist-body">
              <div className="blocklist-input-row">
                <input
                  id="blocklist-input"
                  type="text"
                  className="blocklist-input"
                  placeholder="Add keyword to block…"
                  value={newKeyword}
                  onChange={(e) => setNewKeyword(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") addKeyword();
                  }}
                />
                <button
                  id="btn-add-keyword"
                  className="btn btn-primary btn-sm"
                  onClick={addKeyword}
                >
                  Add
                </button>
              </div>

              {blocklist.length > 0 ? (
                <div className="blocklist-tags">
                  {blocklist.map((kw) => (
                    <span key={kw} className="blocklist-tag">
                      {kw}
                      <button
                        className="blocklist-tag-remove"
                        onClick={() => removeKeyword(kw)}
                        aria-label={`Remove ${kw} from blocklist`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              ) : (
                <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                  No blocked keywords yet.
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="popup-footer">
        <span>
          {lastSyncAt !== null
            ? `Last sync: ${new Date(lastSyncAt).toLocaleTimeString()}`
            : "Never synced"}
        </span>
        <a href="https://contextbridge.ai" target="_blank" rel="noreferrer">
          contextbridge.ai
        </a>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Import Schema Validator
// ---------------------------------------------------------------------------

function validateImportPayload(data: unknown): string | null {
  if (typeof data !== "object" || data === null) {
    return "Root value must be a JSON object.";
  }

  const d = data as Record<string, unknown>;

  if (typeof d["sourcePlatform"] !== "string") {
    return "Missing or invalid 'sourcePlatform' field (must be a string).";
  }

  if (!Array.isArray(d["messages"])) {
    return "Missing or invalid 'messages' field (must be an array).";
  }

  for (let i = 0; i < (d["messages"] as unknown[]).length; i++) {
    const msg = (d["messages"] as unknown[])[i];
    if (typeof msg !== "object" || msg === null) {
      return `Message at index ${i} is not an object.`;
    }
    const m = msg as Record<string, unknown>;
    if (typeof m["role"] !== "string") {
      return `Message at index ${i} is missing 'role' (string).`;
    }
    if (typeof m["text"] !== "string") {
      return `Message at index ${i} is missing 'text' (string).`;
    }
    if (typeof m["timestamp"] !== "string") {
      return `Message at index ${i} is missing 'timestamp' (string).`;
    }
  }

  if (typeof d["checksum"] !== "string") {
    return "Missing or invalid 'checksum' field (must be a string).";
  }

  if (typeof d["capturedAt"] !== "string") {
    return "Missing or invalid 'capturedAt' field (must be a string).";
  }

  return null;
}
