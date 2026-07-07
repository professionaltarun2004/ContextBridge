# ContextBridge — Architectural Principles (RFC 000)

This document defines the non-negotiable rules of the ContextBridge platform. 
As the system evolves to integrate new AI tools, memory providers, and environments, every contributor and adapter must adhere to these invariants. ContextBridge is not a tool; it is an operating system for AI memory.

---

## 1. Memory is Canonical; Embeddings are Indexes.
Embeddings (vector data) are highly volatile and inherently tied to the specific LLM that generated them. Memory Objects are the source of truth. A single Memory Object may have zero, one, or multiple embeddings attached to it. **Never store vector data directly inside a Memory Object.**

## 2. Providers Must Never Bypass the Kernel.
Every external source (Genesis Kit, Git, Browser Extension, Notion, Slack) is a "Driver." A Driver's only responsibility is to read its native format and translate it into the Application Binary Interface (ABI) of ContextBridge: the **Memory Object**. Providers are explicitly forbidden from interacting directly with the Retrieval Engine, the LLM, or the Context Assembler.

## 3. Strict Separation of Concerns in the Pipeline.
The context pipeline is strictly linear and single-responsibility:
1. **The Planner Plans:** It decides *what* type of memory is needed based on intent, without knowing where it lives.
2. **The Retriever Retrieves:** It executes the plan against the database. It contains no intelligence or ranking logic.
3. **The Assembler Assembles:** It merges retrieved objects into a cohesive, unified structure.
4. **The Formatter Formats:** It translates the assembled structure into the specific prompt syntax optimized for the target AI (e.g., Claude, Cursor, GPT).
*No layer may take on another's responsibility.*

## 4. Capabilities Over Providers.
The Planner must never request data from a specific provider (e.g., `if provider == "genesis"`). Instead, the platform relies on a **Capability Registry**. The Planner asks for capabilities (e.g., "I need a provider capable of supplying the latest *Checkpoint*"), and the Registry routes the request. This guarantees that new providers can be hot-swapped without rewriting the Planner.

## 5. Humans are the Ultimate Authority.
ContextBridge operates on collaborative memory. AI can propose new memory nodes, relationships, and evidence, but it cannot silently rewrite canonical memory. If a human edits a Memory Object, that change propagates instantly across all connected systems.

## 6. Evidence is Immutable; Memory is Versioned.
Memory represents synthesized state (e.g., "Use Redis instead of Valkey"). Evidence represents the immutable artifacts (Conversation #51, Benchmark.pdf, Git Commit) that support that memory. 
When a memory evolves, it is **versioned** (tracked via `memory_versions`), and its supporting Evidence remains intact. This guarantees explainability: an AI can always answer *why* it believes a certain fact.

## 7. The Planner is Deterministic.
Do not use an LLM to blindly retrieve memory ("LLM, choose the memories you need"). The Planner relies on graph traversal algorithms, capabilities, heuristic scoring (freshness decay, calculated confidence, frequency importance), and deterministic logic. LLMs are strictly reserved for parsing ambiguous human intent, maintaining low latency and deterministic reliability.
