# ContextOS — The Operating System for AI Work

> **Frictionless AI context transfer. Switch between ChatGPT, Claude, Gemini, and local models without ever repeating yourself.**

[![E2E Smoke Tests](https://github.com/professionaltarun2004/ContextBridge/actions/workflows/e2e-smoke.yml/badge.svg)](https://github.com/professionaltarun2004/ContextBridge/actions/workflows/e2e-smoke.yml)

---

## Overview

ContextOS is a cross-browser extension, interactive web dashboard, and serverless Neo4j backend that solves the **context fragmentation problem** for multi-LLM users. 

When you switch between AI assistants, your conversation history is automatically captured by the Chrome extension, broken down into a Knowledge Graph (Tasks, Decisions, Entities, Constraints), and compiled into an intelligent **Smart Context Pack** that any AI can instantly understand.

### Supported Platforms
| Platform | Scraping | Injection |
|----------|----------|-----------|
| ChatGPT (chatgpt.com) | ✅ | ✅ |
| Claude (claude.ai) | ✅ | ✅ |
| Gemini (gemini.google.com) | ✅ | ✅ |
| Local (Ollama, LM Studio) | ✅ | ✅ |

---

## Architecture (Hackathon MVP)

```
Browser Extension (TypeScript + React)
├── Domain-Isolated Scrapers     → chatgpt.ts, claude.ts, gemini.ts
├── Context Injector             → injector.ts
└── Popup UI                     → App.tsx (Sync context to backend)

Web Dashboard (React + Base44)
├── Knowledge Graph Visualizer   → Renders the Neo4j Graph
└── Context Pack Compiler        → Generates Ultimate-Context-Pack.md

SaaS Backend (Python + FastAPI)
├── POST /api/v1/import          → Multi-agent parallel graph extraction
├── POST /api/v1/compile         → Traverses graph to build Context Packs
└── GET  /api/v1/graph           → Fetches Neo4j edges and nodes
```

---

## Live Deployments

- **Backend API**: `https://contextbridge-qvxc.onrender.com`
- **Dashboard**: Hosted on Vercel
- **Database**: Serverless Neo4j AuraDB

---

## Getting Started

### Prerequisites
- Node.js 22+
- Python 3.12+ (Only needed for local backend dev)

### 1. Build and Install the Chrome Extension

```bash
# Enter the extension directory
cd extension

# Install dependencies and build
npm install
npm run build
```

**Load into Chrome:**
1. Open `chrome://extensions/`
2. Enable **Developer Mode**
3. Click **Load unpacked** → Select the `extension/dist/` directory.

### 2. Using the ContextBridge Flow
1. **Capture**: Open Claude or ChatGPT, have a project conversation, open the Extension Popup, and click **"↑ Sync"**.
2. **Compile**: Go to your Web Dashboard, navigate to **Context Packs**, and click **Compile**. Your entire conversation graph is converted into a ready-to-use Markdown file.
3. **Bridge**: Open a new AI (e.g., ChatGPT), paste the Context Pack, and seamlessly continue your work!

---

## Local Development (Optional)

If you want to run the FastAPI backend locally:

```bash
cd backend
cp .env.example .env

# Edit .env with your OPENROUTER_API_KEY and NEO4J credentials
pip install -r requirements.txt

# Run the local server
uvicorn app.main:app --reload
```
*(Note: There is no PostgreSQL or Alembic setup required. The architecture is fully Neo4j-native.)*

---

## Security & PII

- **Client-Side Redaction**: Passwords and PII are stripped before they leave the browser.
- **Stateless Middlemen**: LiteLLM/OpenRouter agents process extraction strictly in-memory.
- **Graph Isolation**: All memory nodes are stored securely in Neo4j AuraDB.

---

## License

MIT © ContextOS (formerly ContextBridge)
