/**
 * Domain-Isolated Context Injector
 * Injected on ALL supported platforms to handle context injection.
 * Detects target text areas and renders the context badge.
 *
 * FR-004: Context injection UI < 300ms from tab focus.
 * AC4: Decoupled from scraper logic.
 */

import type { ExtensionMessage } from "../types/index";

// ---------------------------------------------------------------------------
// Target Input Area Selectors — ordered by specificity
// ---------------------------------------------------------------------------

const INPUT_SELECTORS = [
  // ChatGPT
  "#prompt-textarea",
  "[data-id='root'] textarea",
  // Claude
  "[contenteditable='true'][data-placeholder]",
  ".ProseMirror[contenteditable='true']",
  // Gemini
  "rich-textarea .ql-editor",
  "[contenteditable='true']",
  // Generic textarea fallback
  "textarea[placeholder*='message' i]",
  "textarea[placeholder*='ask' i]",
  "textarea",
] as const;

const BADGE_ID = "contextbridge-badge";
const BADGE_CONTAINER_ID = "contextbridge-container";

// ---------------------------------------------------------------------------
// DOM Detection — < 300ms requirement
// ---------------------------------------------------------------------------

/**
 * Finds the active prompt input element using ordered selector strategies.
 * Returns null immediately if no match is found (non-blocking).
 */
function detectInputElement(): HTMLElement | null {
  for (const selector of INPUT_SELECTORS) {
    const el = document.querySelector<HTMLElement>(selector);
    if (el !== null && isVisible(el)) {
      return el;
    }
  }
  return null;
}

/**
 * Checks whether an element is visually present in the viewport.
 */
function isVisible(el: HTMLElement): boolean {
  const rect = el.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

// ---------------------------------------------------------------------------
// Badge Rendering
// ---------------------------------------------------------------------------

/**
 * Creates the ContextBridge overlay badge and appends it to the DOM.
 * Positioned relative to the detected input element.
 */
function renderBadge(
  inputEl: HTMLElement,
  summaryText: string,
  onInject: (text: string) => void
): void {
  // Remove existing badge if present
  document.getElementById(BADGE_CONTAINER_ID)?.remove();

  const container = document.createElement("div");
  container.id = BADGE_CONTAINER_ID;
  container.setAttribute("data-contextbridge", "true");

  const badge = document.createElement("button");
  badge.id = BADGE_ID;
  badge.setAttribute("type", "button");
  badge.setAttribute("aria-label", "Inject ContextBridge context");

  // Styling — injected directly to avoid conflicting with host page CSS
  Object.assign(container.style, {
    position: "fixed",
    zIndex: "2147483647",
    pointerEvents: "none",
  });

  Object.assign(badge.style, {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    padding: "6px 12px",
    background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
    color: "#ffffff",
    border: "none",
    borderRadius: "20px",
    fontSize: "13px",
    fontFamily: "'Inter', system-ui, sans-serif",
    fontWeight: "600",
    cursor: "pointer",
    boxShadow: "0 4px 16px rgba(99, 102, 241, 0.4)",
    transition: "transform 0.15s ease, box-shadow 0.15s ease",
    pointerEvents: "all",
    letterSpacing: "0.01em",
  });

  badge.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
    <span>Inject Context</span>
  `;

  badge.addEventListener("mouseenter", () => {
    badge.style.transform = "scale(1.05)";
    badge.style.boxShadow = "0 6px 20px rgba(99, 102, 241, 0.55)";
  });

  badge.addEventListener("mouseleave", () => {
    badge.style.transform = "scale(1)";
    badge.style.boxShadow = "0 4px 16px rgba(99, 102, 241, 0.4)";
  });

  badge.addEventListener("click", async () => {
    // Pulse animation on click
    badge.style.transform = "scale(0.95)";
    setTimeout(() => {
      badge.style.transform = "scale(1)";
    }, 150);

    const span = badge.querySelector("span");
    if (span) span.innerText = "Compiling Pack...";

    try {
      // 1. Check for available packs (as required)
      await fetch("http://localhost:8000/api/v1/packs");

      // 2. Pull the actual compiled payload
      const compileRes = await fetch("http://localhost:8000/api/v1/compile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: "conv_mock_001",
          role_pack: "backend",
          selections: { architecture: true, apis: true, database: true, constraints: true }
        })
      });
      
      const compileData = await compileRes.json();
      
      let textToInject = "";
      if (compileData && compileData.files) {
        textToInject = Object.entries(compileData.files)
          .map(([name, content]) => `## ${name}\n\n${content as string}`)
          .join('\n\n---\n\n');
      } else {
        textToInject = summaryText; // Fallback
      }

      onInject(textToInject);
      if (span) span.innerText = "Injected ✓";
      setTimeout(() => removeBadge(), 2000);

    } catch (e) {
      console.error("ContextOS fetch failed:", e);
      // Fallback to local context cache if backend is unreachable
      onInject(summaryText);
      if (span) span.innerText = "Injected ✓ (Offline)";
      setTimeout(() => removeBadge(), 2000);
    }
  });

  container.appendChild(badge);
  document.body.appendChild(container);

  // Position badge near the input element
  positionBadge(container, inputEl);
}

/**
 * Positions the badge container near the detected input element.
 */
function positionBadge(
  container: HTMLDivElement,
  inputEl: HTMLElement
): void {
  const rect = inputEl.getBoundingClientRect();
  Object.assign(container.style, {
    top: `${rect.top - 48}px`,
    right: `${window.innerWidth - rect.right}px`,
  });
}

// ---------------------------------------------------------------------------
// Context Injection — FR-004, AC3
// ---------------------------------------------------------------------------

/**
 * Injects sanitized summary text into the target input element.
 * Supports both <textarea> elements and contenteditable divs.
 * Fires native input and change events so React/Vue state updates correctly.
 */
function injectContextIntoInput(inputEl: HTMLElement, text: string): void {
  if (
    inputEl instanceof HTMLTextAreaElement ||
    inputEl instanceof HTMLInputElement
  ) {
    // For native textarea elements
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype,
      "value"
    )?.set;

    if (nativeInputValueSetter !== undefined) {
      nativeInputValueSetter.call(inputEl, text);
    } else {
      inputEl.value = text;
    }

    inputEl.dispatchEvent(new Event("input", { bubbles: true }));
    inputEl.dispatchEvent(new Event("change", { bubbles: true }));
  } else if (inputEl.isContentEditable) {
    // For contenteditable elements (Claude, Gemini)
    inputEl.focus();
    document.execCommand("selectAll", false);
    document.execCommand("insertText", false, text);
    inputEl.dispatchEvent(new InputEvent("input", { bubbles: true }));
  }
}

// ---------------------------------------------------------------------------
// Main Injector Logic
// ---------------------------------------------------------------------------

let currentSummary: string | null = null;

/**
 * Starts the < 300ms detection loop on tab focus.
 * Uses requestAnimationFrame-based polling for maximum responsiveness.
 */
function startDetection(summary: string): void {
  currentSummary = summary;

  const startTime = performance.now();

  const detect = (): void => {
    const elapsed = performance.now() - startTime;

    if (elapsed > 300) {
      // Detection budget exceeded — give up this cycle
      return;
    }

    const inputEl = detectInputElement();

    if (inputEl !== null) {
      renderBadge(inputEl, summary, (text) => {
        injectContextIntoInput(inputEl, text);
      });
      return;
    }

    // Keep trying within the 300ms window
    requestAnimationFrame(detect);
  };

  requestAnimationFrame(detect);
}

/**
 * Cleans up the badge when no context is available.
 */
function removeBadge(): void {
  document.getElementById(BADGE_CONTAINER_ID)?.remove();
  currentSummary = null;
}

// ---------------------------------------------------------------------------
// Message Listener — receives commands from the background worker
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message: ExtensionMessage) => {
  if (message.type === "CONTEXT_AVAILABLE") {
    startDetection(message.summary);
  } else if (message.type === "INJECT_CONTEXT") {
    const inputEl = detectInputElement();
    if (inputEl !== null) {
      injectContextIntoInput(inputEl, message.summary);
    }
    removeBadge();
  }
});

// Re-position badge on scroll/resize
window.addEventListener("resize", () => {
  if (currentSummary !== null) {
    const inputEl = detectInputElement();
    const container = document.getElementById(
      BADGE_CONTAINER_ID
    ) as HTMLDivElement | null;
    if (inputEl !== null && container !== null) {
      positionBadge(container, inputEl);
    }
  }
});

// Trigger detection on initial load in case context is already available
chrome.runtime.sendMessage({ type: "GET_STATE", requestId: "injector-init" });

chrome.runtime.onMessage.addListener((message: ExtensionMessage) => {
  if (
    message.type === "STATE_RESPONSE" &&
    message.requestId === "injector-init"
  ) {
    const summary = message.state.activePayload?.messages
      .map((m) => `${m.role}: ${m.text}`)
      .join("\n");
    if (summary !== undefined && summary.length > 0) {
      startDetection(summary);
    }
  }
});
