import { useEffect, useState } from 'react';
import { api, type GraphResponse } from '../api';

type Page = 'overview' | 'projects' | 'timeline' | 'graph' | 'packs' | 'export';

interface Props { onNavigate: (page: Page) => void; }

const MOCK_STATS = { nodes: 12, relationships: 9, conversations: 3, confidence: '96%' };

export default function Overview({ onNavigate }: Props) {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);

  useEffect(() => {
    api.graph().then(setGraph).catch(console.error);
  }, []);

  const handleQuickImport = async () => {
    setImporting(true);
    setImportResult(null);
    try {
      const result = await api.import({
        platform: 'claude',
        url: 'https://claude.ai/demo',
        messages: [
          { id: 'msg_1', role: 'user', text: 'Let\'s use FastAPI and Neo4j for the backend. Redis for caching.', timestamp: new Date().toISOString() },
          { id: 'msg_2', role: 'assistant', text: 'FastAPI is perfect. Neo4j gives us graph relationships, and Redis handles our cache layer efficiently.', timestamp: new Date().toISOString() },
          { id: 'msg_3', role: 'user', text: 'We need to deploy on Render with Docker. The pipeline must run under 10 seconds.', timestamp: new Date().toISOString() },
        ],
      });
      setImportResult(`✓ Imported! ${result.nodes_extracted} nodes · ${result.relationships_created} relationships · ${result.execution_time_ms}ms`);
      api.graph().then(setGraph).catch(console.error);
    } catch (e) {
      setImportResult('Backend offline — running in MOCK_MODE');
    } finally {
      setImporting(false);
    }
  };

  const nodeCount = graph?.nodes.length ?? MOCK_STATS.nodes;
  const edgeCount = graph?.edges.length ?? MOCK_STATS.relationships;

  return (
    <div className="fade-in">
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <div>
            <div className="page-title">The OS for AI Work</div>
            <div className="page-subtitle">Continue any AI conversation from exactly where you left off.</div>
          </div>
          <button className="btn btn-primary glow" onClick={handleQuickImport} disabled={importing}>
            {importing ? '⟳ Importing...' : '⚡ Quick Import'}
          </button>
        </div>
        {importResult && (
          <div className="citation fade-in" style={{ marginTop: 12 }}>
            <strong>{importResult}</strong>
          </div>
        )}
      </div>

      <div className="page-content">
        {/* KPI Row */}
        <div className="grid-4" style={{ marginBottom: 24 }}>
          <div className="kpi-card">
            <div className="kpi-label">Graph Nodes</div>
            <div className="kpi-value" style={{ color: 'var(--accent)' }}>{nodeCount}</div>
            <div className="kpi-sub">memories indexed</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Relationships</div>
            <div className="kpi-value" style={{ color: 'var(--cyan)' }}>{edgeCount}</div>
            <div className="kpi-sub">graph edges</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Conversations</div>
            <div className="kpi-value" style={{ color: 'var(--green)' }}>{MOCK_STATS.conversations}</div>
            <div className="kpi-sub">sources imported</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Avg Confidence</div>
            <div className="kpi-value" style={{ color: 'var(--amber)' }}>{MOCK_STATS.confidence}</div>
            <div className="kpi-sub">extraction accuracy</div>
          </div>
        </div>

        <div className="grid-2">
          {/* Recent Captures */}
          <div className="card">
            <div className="card-title">Recent Captures</div>
            {[
              { platform: 'Claude', title: 'ContextOS Backend Architecture', time: '2m ago', nodes: 12 },
              { platform: 'ChatGPT', title: 'Neo4j Schema Design', time: '1h ago', nodes: 8 },
              { platform: 'Gemini', title: 'Frontend Dashboard Planning', time: '3h ago', nodes: 6 },
            ].map((c, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: i < 2 ? '1px solid var(--border-subtle)' : 'none' }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 3 }}>{c.title}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{c.platform} · {c.time}</div>
                </div>
                <div className="badge badge-accent">{c.nodes} nodes</div>
              </div>
            ))}
          </div>

          {/* Quick Actions */}
          <div className="card">
            <div className="card-title">Quick Actions</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[
                { label: '🔮 View Knowledge Graph', page: 'graph' as Page },
                { label: '📦 Compile Context Pack', page: 'packs' as Page },
                { label: '⏱ Audit Timeline', page: 'timeline' as Page },
                { label: '↗ Export to IDE', page: 'export' as Page },
              ].map((action) => (
                <button key={action.label} className="btn btn-secondary" style={{ justifyContent: 'flex-start' }} onClick={() => onNavigate(action.page)}>
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Node preview */}
        {graph && graph.nodes.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <div className="section-label">Graph Snapshot</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {graph.nodes.slice(0, 10).map((n) => {
                const colors: Record<string, string> = { Decision: 'var(--accent)', Task: 'var(--cyan)', Entity: 'var(--green)', Constraint: 'var(--amber)', Conversation: 'var(--text-secondary)' };
                return (
                  <div key={n.id} className="node-chip">
                    <span className="node-dot" style={{ background: colors[n.label] ?? 'var(--text-muted)' }} />
                    <span>{String((n.properties as Record<string, unknown>).text ?? (n.properties as Record<string, unknown>).name ?? n.label)}</span>
                    <span className="tag">{n.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
