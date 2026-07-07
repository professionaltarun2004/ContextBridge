# ContextBridge — SharedMemory AI

> **Frictionless AI context transfer. Switch between ChatGPT, Claude, Gemini, and local models without ever repeating yourself.**

[![E2E Smoke Tests](https://github.com/your-org/contextbridge/actions/workflows/e2e-smoke.yml/badge.svg)](https://github.com/your-org/contextbridge/actions/workflows/e2e-smoke.yml)

---

## Overview

ContextBridge is a cross-browser extension and SaaS backend that solves the **context fragmentation problem** for multi-LLM users. When you switch between AI assistants (due to rate limits, capability differences, or preference), your conversation history is automatically captured, sanitized, AI-summarized, and injected into your new session with a single click.

### Supported Platforms
| Platform | Scraping | Injection |
|----------|----------|-----------|
| ChatGPT (chatgpt.com) | ✅ | ✅ |
| Claude (claude.ai) | ✅ | ✅ |
| Gemini (gemini.google.com) | ✅ | ✅ |
| Local (Ollama, LM Studio, Open WebUI) | ✅ | ✅ |

---

## Architecture

```
Browser Extension (TypeScript + React)
├── Domain-Isolated Scrapers     → chatgpt.ts, claude.ts, gemini.ts, localhost.ts
├── Context Injector             → injector.ts (< 300ms badge detection)
├── Background Service Worker    → worker.ts (sync, tab events, offline fallback)
└── Popup UI                     → App.tsx (export/import, blocklist, sync)

SaaS Backend (Python + FastAPI)
├── POST /api/v1/sync            → Generate summary + store embeddings
├── GET  /api/v1/context         → Semantic vector search (pgvector)
├── POST /api/v1/telemetry/scraper-error → DOM failure alerts
└── POST /api/v1/stripe/webhook  → Subscription lifecycle management
```

---

## Getting Started

### Prerequisites
- Node.js 22+
- Python 3.12+
- Docker & Docker Compose

### 1. Start Backend Services

```bash
# Copy and configure environment
cp backend/.env.example backend/.env
# Fill in AUTH0_DOMAIN, OPENAI_API_KEY, STRIPE keys, etc.

# Start PostgreSQL + Redis + API
docker-compose up --build

# Run database migrations (first time)
cd backend
pip install -r requirements.txt
alembic upgrade head
```

### 2. Build the Extension

```bash
cd extension
npm install
npm run build
```

### 3. Load in Chrome/Edge

1. Open `chrome://extensions/`
2. Enable **Developer Mode**
3. Click **Load unpacked** → Select `extension/dist/`
4. The ContextBridge icon appears in your toolbar

---

## Development

### Backend Tests
```bash
cd backend
pip install -r requirements.txt
pytest --cov=app --cov-fail-under=80
```

### Extension Typecheck
```bash
cd extension
npm run typecheck
```

### Live E2E Smoke Tests (manual)
```bash
cd extension
npx playwright test tests/smoke
```

---

## Security

- All sensitive state stored in `chrome.storage.local` (isolated sandbox)
- JWT verification via Auth0 RS256 + JWKS
- Stripe webhook signature validation on every event
- Client-side PII redaction before any network transit
- Server-side PII leak scan on incoming payloads
- TLS 1.3 enforced for all API communication
- Row-level security on all database queries (user_id isolation)
- Raw conversation history purged after 24 hours

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL asyncpg connection string |
| `AUTH0_DOMAIN` | ✅ | Auth0 tenant domain |
| `AUTH0_AUDIENCE` | ✅ | Auth0 API audience |
| `STRIPE_SECRET_KEY` | ✅ | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | ✅ | Stripe webhook signing secret |
| `OPENAI_API_KEY` | ✅ | OpenAI API key (summarization + embeddings) |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API key (Claude preset) |
| `REDIS_URL` | — | Redis connection URL (default: `redis://localhost:6379/0`) |
| `SENTRY_DSN` | — | Sentry error collection DSN |

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Tab injection detection | < 300ms | rAF-based timing in injector.ts |
| Summarization latency | < 1.5s overall / < 200ms TTFT | LiteLLM streaming with 1.4s timeout |
| DOM smoke tests | Every 6 hours | GHA cron + Slack/email alerts |
| Test coverage | ≥ 80% | pytest-cov on backend |

---

## License

MIT © ContextBridge
