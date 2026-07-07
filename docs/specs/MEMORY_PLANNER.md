# ContextBridge — The Memory Pipeline (RFC 002)

## Philosophy
ContextBridge is fundamentally opposed to standard naive RAG (Retrieve-Augment-Generate). Searching a vector database for semantic similarity is the *last* step of retrieval, not the first.

ContextBridge operates a rigid, multi-stage pipeline designed to mimic an operating system's query optimizer.

---

## The Execution Pipeline

### 1. Intent Parser
**Input:** Raw user prompt ("Continue implementing OAuth.")
**Responsibility:** Translates ambiguous text into a structured intent object. (This is the only stage where an LLM may be used for classification).

### 2. Memory Planner
**Responsibility:** "What kind of memory is required?"
* Evaluates the Intent against the **Capability Registry**.
* Generates an Execution Plan.
* *Example Output:*
  * **Need:** Architecture (depth=2), Current Checkpoint, Open Bugs.
  * **Ignore:** Meeting notes, old conversations.
  * **Budget:** 25 Memory Objects.

### 3. Capability Registry & Provider Selection
**Responsibility:** Routes the Execution Plan to the appropriate active drivers.
* *Planner asks:* "Who can provide Checkpoints?"
* *Registry answers:* "GenesisAdapter, BrowserExtensionAdapter."

### 4. Retriever & Graph Expansion
**Responsibility:** Executes the deterministic retrieval plan against the database.
* Identifies root nodes (e.g., "OAuth").
* **Graph Expansion:** Automatically traverses relationships (`depends_on`, `implements`) to pull in required context (e.g., "OAuth -> JWT -> Supabase").
* Pulls **Evidence** supporting the retrieved nodes.

### 5. Ranking Engine
**Responsibility:** Sorts and trims the retrieved subgraph to fit the Memory Budget.
* Uses calculated heuristics, not arbitrary stored values.
* **Confidence:** Derived from evidence count, human verification, and cross-provider agreement.
* **Importance:** Derived from reference frequency in the graph.
* **Freshness:** Automatically decays over time (e.g., 1.0 at day 0 -> 0.38 at day 90).
* *Embeddings* are used here strictly as a secondary sorting filter for semantic relevance within the active subgraph.

### 6. Assembler
**Responsibility:** "Merge"
* Merges the filtered, ranked nodes into a single Unified Context Object. 
* Resolves version conflicts.

### 7. Formatter (AI Adapters)
**Responsibility:** Translates the Unified Context Object into provider-specific prompts.
* **Claude Adapter:** Prefers heavy `<reasoning>` tags and XML structures.
* **Cursor Adapter:** Prefers `@file` formatting and strict task constraints.
* **GPT Adapter:** Prefers markdown summaries and system instructions.

---

## Conclusion
By isolating these responsibilities, ContextBridge ensures that the intelligence is in the *planning and relationship traversal*, not just the embedding search. This guarantees a context payload that is highly relevant, explicitly explainable (via Evidence), and strictly budgeted.
