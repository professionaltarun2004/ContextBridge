import { useEffect, useState } from 'react';
import { api, type GraphResponse, type GraphNode, type GraphEdge } from '../api';

const LABEL_COLORS: Record<string, string> = {
  Conversation: '#8892b0',
  Decision: '#6c63ff',
  Task: '#00d4ff',
  Entity: '#00e5a0',
  Constraint: '#f59e0b',
  Prompt: '#ff4757',
  ContextPack: '#ff6b9d',
};

function NodePanel({ node, onClose }: { node: GraphNode; onClose: () => void }) {
  const props = node.properties as Record<string, unknown>;
  const conf = (props.confidence as number) ?? null;
  return (
    <div style={{
      position: 'absolute', right: 20, top: 20, width: 300,
      background: 'var(--bg-elevated)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', padding: 20, zIndex: 10,
    }} className="fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <div className="badge" style={{ background: LABEL_COLORS[node.label] + '22', color: LABEL_COLORS[node.label] }}>
          {node.label}
        </div>
        <button className="btn btn-ghost" style={{ padding: '0 6px' }} onClick={onClose}>✕</button>
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
        {String(props.text ?? props.name ?? props.title ?? node.id)}
      </div>
      {conf !== null && (
        <div style={{ marginBottom: 12 }}>
          <div className="kpi-label" style={{ marginBottom: 6 }}>Confidence</div>
          <div className="conf-bar">
            <div className="conf-track">
              <div className="conf-fill" style={{ width: `${conf * 100}%`, background: conf > 0.9 ? 'var(--green)' : conf > 0.7 ? 'var(--amber)' : 'var(--red)' }} />
            </div>
            <span className="conf-label" style={{ color: conf > 0.9 ? 'var(--green)' : 'var(--amber)' }}>{(conf * 100).toFixed(0)}%</span>
          </div>
        </div>
      )}
      {(props.source_ai as string | undefined) && (
        <div className="citation">
          <strong>Source:</strong> {String(props.source_ai)} · msg <code>{String(props.source_message)}</code>
        </div>
      )}
      {(props.rationale as string | undefined) && (
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>Rationale:</strong> {String(props.rationale)}
        </div>
      )}
    </div>
  );
}

function GraphCanvas({ nodes, edges, onSelectNode }: { nodes: GraphNode[]; edges: GraphEdge[]; onSelectNode: (n: GraphNode) => void }) {
  // Simple SVG force-directed layout simulation (static for V1)
  const W = 760, H = 480;
  const cx = W / 2, cy = H / 2;
  const total = nodes.length;

  const positions = nodes.map((_, i) => {
    if (total === 1) return { x: cx, y: cy };
    const angle = (2 * Math.PI * i) / total;
    const r = Math.min(W, H) * 0.32;
    return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
  });

  const posMap: Record<string, { x: number; y: number }> = {};
  nodes.forEach((n, i) => { posMap[n.id] = positions[i]; });

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ background: 'var(--bg-base)', borderRadius: 'var(--radius-lg)' }}>
      <defs>
        <radialGradient id="bg-grad" cx="50%" cy="50%">
          <stop offset="0%" stopColor="#161a26" />
          <stop offset="100%" stopColor="#0a0b0f" />
        </radialGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      <rect width={W} height={H} fill="url(#bg-grad)" />

      {/* Edges */}
      {edges.map((e) => {
        const s = posMap[e.source];
        const t = posMap[e.target];
        if (!s || !t) return null;
        return (
          <g key={e.id}>
            <line x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke="#1f2437" strokeWidth="1.5" strokeDasharray="4 4" />
            <text x={(s.x + t.x) / 2} y={(s.y + t.y) / 2 - 4} fontSize="9" fill="#4a5568" textAnchor="middle">{e.type}</text>
          </g>
        );
      })}

      {/* Nodes */}
      {nodes.map((n, i) => {
        const { x, y } = positions[i];
        const color = LABEL_COLORS[n.label] ?? '#8892b0';
        const props = n.properties as Record<string, unknown>;
        const label = String(props.text ?? props.name ?? n.label).slice(0, 20);
        const conf = (props.confidence as number) ?? 0.8;
        const r = n.label === 'Conversation' ? 18 : 13;
        return (
          <g key={n.id} style={{ cursor: 'pointer' }} onClick={() => onSelectNode(n)}>
            <circle cx={x} cy={y} r={r + 6} fill={color} opacity={0.08} />
            <circle cx={x} cy={y} r={r} fill={color + '22'} stroke={color} strokeWidth="1.5" filter="url(#glow)" />
            <circle cx={x} cy={y} r={4} fill={color} />
            <text x={x} y={y + r + 14} fontSize="10" fill="var(--text-secondary)" textAnchor="middle">{label}</text>
            {conf > 0 && (
              <text x={x} y={y + r + 24} fontSize="9" fill={conf > 0.9 ? 'var(--green)' : 'var(--amber)'} textAnchor="middle">{(conf * 100).toFixed(0)}%</text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

export default function KnowledgeGraph() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<GraphNode | null>(null);

  useEffect(() => {
    api.graph().then(setGraph).catch(console.error).finally(() => setLoading(false));
  }, []);

  const nodesByType = (graph?.nodes ?? []).reduce<Record<string, number>>((acc, n) => {
    acc[n.label] = (acc[n.label] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="fade-in">
      <div className="page-header">
        <div className="page-title">Knowledge Graph</div>
        <div className="page-subtitle">Interactive map of your AI decisions, tasks, and relationships.</div>
      </div>

      <div className="page-content">
        {/* Legend */}
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
          {Object.entries(LABEL_COLORS).map(([label, color]) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-secondary)' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
              {label} {nodesByType[label] ? `(${nodesByType[label]})` : ''}
            </div>
          ))}
        </div>

        <div style={{ position: 'relative' }}>
          {loading ? (
            <div style={{ padding: 80, textAlign: 'center', color: 'var(--text-muted)' }}>
              <div className="pulse">Loading graph...</div>
            </div>
          ) : graph && graph.nodes.length > 0 ? (
            <GraphCanvas nodes={graph.nodes} edges={graph.edges} onSelectNode={setSelected} />
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">⬡</div>
              <div className="empty-state-title">No graph data yet</div>
              <div className="empty-state-sub">Import a conversation from the Overview page to populate the graph.</div>
            </div>
          )}
          {selected && <NodePanel node={selected} onClose={() => setSelected(null)} />}
        </div>

        {/* Node table */}
        {graph && graph.nodes.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <div className="section-label">All Nodes ({graph.nodes.length})</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {graph.nodes.map((n) => {
                const props = n.properties as Record<string, unknown>;
                const color = LABEL_COLORS[n.label] ?? '#8892b0';
                const conf = props.confidence as number | undefined;
                return (
                  <div key={n.id} className="card" style={{ padding: '10px 16px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 12 }}
                    onClick={() => setSelected(n)}>
                    <div className="node-dot" style={{ background: color, width: 8, height: 8 }} />
                    <div style={{ flex: 1, fontSize: 13 }}>{String(props.text ?? props.name ?? n.label)}</div>
                    <div className="badge" style={{ background: color + '22', color }}>{n.label}</div>
                    {conf !== undefined && (
                      <div style={{ fontSize: 11, color: conf > 0.9 ? 'var(--green)' : 'var(--amber)', minWidth: 36 }}>
                        {(conf * 100).toFixed(0)}%
                      </div>
                    )}
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
