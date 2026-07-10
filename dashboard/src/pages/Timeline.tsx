import { useState } from 'react';
import { api, type AskResponse } from '../api';

const TIMELINE_EVENTS = [
  {
    icon: '🔄',
    color: 'var(--accent)',
    title: 'Database Switched to Neo4j',
    meta: 'Today 10:02 AM · Claude',
    body: 'Switched from PostgreSQL + pgvector to Neo4j AuraDB for complex relationship traversal needs. This decision affects the entire storage and retrieval layer.',
    affected: ['Database Schema', 'Retrieval Engine', 'Cypher Driver', 'Docker Config'],
    confidence: 0.97,
  },
  {
    icon: '⚡',
    color: 'var(--cyan)',
    title: 'Parallel Agent Pipeline Added',
    meta: 'Today 09:45 AM · Claude',
    body: 'Entity, Decision, Task, and Constraint agents now run concurrently via asyncio.gather. Pipeline executes in under 10 seconds.',
    affected: ['pipeline.py', 'Entity Agent', 'Decision Agent'],
    confidence: 0.95,
  },
  {
    icon: '📦',
    color: 'var(--green)',
    title: 'Smart Context Packs Defined',
    meta: 'Yesterday 04:30 PM · ChatGPT',
    body: 'Introduced role-specific Smart Packs: Backend, Frontend, DevOps, and BugFix. Each compiles the relevant architectural sections.',
    affected: ['pack_generator.py', 'Context Packs UI'],
    confidence: 0.92,
  },
  {
    icon: '🔑',
    color: 'var(--amber)',
    title: 'Auth Strategy Simplified',
    meta: 'Yesterday 02:00 PM · Claude',
    body: 'Removed Auth0 and Stripe for the hackathon sprint. Authentication deferred to Phase 2. Focus shifted to core graph intelligence.',
    affected: ['auth.py (removed)', 'requirements.txt', 'docker-compose.yml'],
    confidence: 0.99,
  },
  {
    icon: '🚀',
    color: 'var(--green)',
    title: 'Deploy Target Set to Render',
    meta: '2 days ago · ChatGPT',
    body: 'Backend containerized with Docker and targeting Render for deployment. Neo4j AuraDB connected via bolt URI environment variable.',
    affected: ['Dockerfile', 'docker-compose.yml', '.env.example'],
    confidence: 0.93,
  },
];

export default function Timeline() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [asking, setAsking] = useState(false);

  const handleAsk = async () => {
    if (!question.trim()) return;
    setAsking(true);
    setAnswer(null);
    try {
      const result = await api.ask(question);
      setAnswer(result);
    } catch {
      setAnswer({ answer: 'Backend offline — run with MOCK_MODE=True to see live answers.', confidence_average: 0, citations: [] });
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <div className="page-title">Timeline</div>
        <div className="page-subtitle">Chronological audit of all architectural decisions and changes.</div>
      </div>

      <div className="page-content">
        {/* Ask bar */}
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-title">Ask ContextOS</div>
          <div className="ask-bar">
            <span style={{ fontSize: 18 }}>💬</span>
            <input
              className="ask-input"
              placeholder='Try "Why did we switch to Neo4j?" or "What auth strategy did we choose?"'
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
            />
            <button className="btn btn-primary" onClick={handleAsk} disabled={asking} style={{ whiteSpace: 'nowrap' }}>
              {asking ? '⟳' : '→ Ask'}
            </button>
          </div>
          {answer && (
            <div className="fade-in" style={{ marginTop: 16 }}>
              <div style={{ fontSize: 14, lineHeight: 1.7, marginBottom: 12 }}>{answer.answer}</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <div className="badge badge-green">
                  {(answer.confidence_average * 100).toFixed(0)}% confidence
                </div>
                {answer.citations.map((c, i) => (
                  <div key={i} className="citation" style={{ display: 'inline-flex', marginTop: 0 }}>
                    <strong>{c.node_label}</strong> · {c.source_ai} · {c.source_message}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Timeline events */}
        <div className="section-label">Decision History</div>
        <div style={{ paddingLeft: 0 }}>
          {TIMELINE_EVENTS.map((event, i) => (
            <div key={i} className="timeline-item">
              <div className="timeline-dot" style={{ background: event.color + '22', borderColor: event.color, color: event.color }}>
                {event.icon}
              </div>
              <div className="timeline-content">
                <div className="timeline-title">{event.title}</div>
                <div className="timeline-meta">{event.meta}</div>
                <div className="timeline-body" style={{ marginBottom: 10 }}>{event.body}</div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                  {event.affected.map((a) => (
                    <span key={a} className="tag">{a}</span>
                  ))}
                </div>
                <div className="conf-bar" style={{ maxWidth: 200 }}>
                  <div className="conf-track">
                    <div className="conf-fill" style={{ width: `${event.confidence * 100}%`, background: event.color }} />
                  </div>
                  <span className="conf-label" style={{ color: event.color }}>{(event.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
