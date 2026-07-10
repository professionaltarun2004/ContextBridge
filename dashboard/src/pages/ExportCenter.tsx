import { useState } from 'react';
import { api } from '../api';

const EXPORT_TARGETS = [
  { id: 'cursor', label: 'Cursor IDE', emoji: '⌨️', desc: 'Paste into .cursorrules for instant context injection', color: 'var(--accent)' },
  { id: 'vscode', label: 'VS Code', emoji: '🔷', desc: 'Save to .context/ directory in workspace root', color: 'var(--cyan)' },
  { id: 'chatgpt', label: 'ChatGPT', emoji: '🤖', desc: 'Copy as system prompt to start a new conversation', color: 'var(--green)' },
  { id: 'claude', label: 'Claude', emoji: '🟣', desc: 'Paste into project knowledge for persistent memory', color: 'var(--amber)' },
  { id: 'zip', label: 'ZIP Download', emoji: '📁', desc: 'Download all pack files as a compressed archive', color: 'var(--text-secondary)' },
];

const MOCK_PACK_CONTENT = `# ContextOS Backend Context Pack
Generated: ${new Date().toLocaleString()}

---

## Architecture

- FastAPI async gateway on Render
- Neo4j AuraDB for graph storage
- LiteLLM for parallel agent orchestration
- Chrome Extension (React + TypeScript)

## API Endpoints

- POST /api/v1/import — Trigger multi-agent pipeline
- POST /api/v1/compile — Compile Smart Context Pack
- GET /api/v1/graph — Fetch Knowledge Graph
- POST /api/v1/ask — Graph traversal Q&A
- GET /api/v1/packs — List generated packs
- POST /api/v1/export — Export pack bundle

## Constraints

- [ ] Pipeline must complete in under 10 seconds
- [ ] Extension must detect text area in under 300ms
- [ ] Strict TypeScript — no implicit any
- [ ] Graph renders under 1 second for up to 1000 nodes

## Current Tasks

- [ ] Build 6-page Base44 Dashboard
- [ ] Connect E2E flow with MOCK_MODE
- [ ] Deploy to Render with Neo4j AuraDB
- [x] Parallel multi-agent pipeline
- [x] Smart Context Pack generator
`;

export default function ExportCenter() {
  const [selectedTarget, setSelectedTarget] = useState('cursor');
  const [exporting, setExporting] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  const handleExport = async () => {
    setExporting(true);
    setDone(null);
    try {
      if (selectedTarget === 'zip') {
        const result = await api.export('pack_mock_001', 'zip');
        setDone(`Download ready: ${result.download_url}`);
      } else {
        await navigator.clipboard.writeText(MOCK_PACK_CONTENT);
        setDone(`✓ Copied to clipboard! Paste directly into ${EXPORT_TARGETS.find((t) => t.id === selectedTarget)?.label}.`);
      }
    } catch {
      await navigator.clipboard.writeText(MOCK_PACK_CONTENT);
      setDone('✓ Copied to clipboard!');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <div className="page-title">Export Center</div>
        <div className="page-subtitle">Send your Context Packs directly to any AI assistant or IDE.</div>
      </div>

      <div className="page-content">
        <div className="grid-2" style={{ alignItems: 'flex-start' }}>
          {/* Target selector */}
          <div>
            <div className="section-label">Export Target</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 24 }}>
              {EXPORT_TARGETS.map((target) => (
                <div
                  key={target.id}
                  className="card"
                  style={{
                    cursor: 'pointer',
                    borderColor: selectedTarget === target.id ? target.color : 'var(--border)',
                    background: selectedTarget === target.id ? target.color + '11' : 'var(--bg-surface)',
                    transition: 'all 0.2s',
                  }}
                  onClick={() => { setSelectedTarget(target.id); setDone(null); }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 20 }}>{target.emoji}</span>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: selectedTarget === target.id ? target.color : 'var(--text-primary)' }}>
                        {target.label}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                        {target.desc}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button
              className="btn btn-primary glow"
              style={{ width: '100%', justifyContent: 'center' }}
              onClick={handleExport}
              disabled={exporting}
            >
              {exporting ? '⟳ Exporting...' : `↗ Export to ${EXPORT_TARGETS.find((t) => t.id === selectedTarget)?.label}`}
            </button>

            {done && (
              <div className="citation fade-in" style={{ marginTop: 12 }}>
                <strong>{done}</strong>
              </div>
            )}
          </div>

          {/* Preview */}
          <div>
            <div className="section-label">Pack Preview</div>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <div className="badge badge-accent">Backend Pack</div>
                <div className="badge badge-green">Ready</div>
              </div>
              <div className="code-block" style={{ maxHeight: 400, overflowY: 'auto' }}>
                {MOCK_PACK_CONTENT}
              </div>
            </div>

            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-title">CLI Copy Script</div>
              <div className="code-block">
                {`# Inject into Cursor workspace
cat backend-pack.md > .cursorrules

# Or pipe directly
contextos export --role backend | cursor --stdin`}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
