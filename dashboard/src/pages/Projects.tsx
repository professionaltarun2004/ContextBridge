import { useState } from 'react';

const REPOS = [
  { name: 'ContextOS Backend', url: 'github.com/professionaltarun2004/ContextBridge', branch: 'main', status: 'active' },
  { name: 'ContextOS Extension', url: 'github.com/professionaltarun2004/ContextBridge', branch: 'main', status: 'active' },
];

const ENV_VARS = [
  { key: 'NEO4J_URI', value: 'neo4j+s://••••••.databases.neo4j.io', status: 'set' },
  { key: 'OPENAI_API_KEY', value: 'sk-dummy', status: 'mock' },
  { key: 'GEMINI_API_KEY', value: 'dummy', status: 'mock' },
  { key: 'MOCK_MODE', value: 'True', status: 'mock' },
  { key: 'APP_ENV', value: 'development', status: 'set' },
];

export default function Projects() {
  const [repoUrl, setRepoUrl] = useState('');
  const [linked, setLinked] = useState(false);

  return (
    <div className="fade-in">
      <div className="page-header">
        <div className="page-title">Projects</div>
        <div className="page-subtitle">Manage workspace repositories, environment profiles, and source mappings.</div>
      </div>

      <div className="page-content">
        <div className="grid-2" style={{ alignItems: 'flex-start' }}>
          <div>
            <div className="section-label">Active Repositories</div>
            {REPOS.map((repo, i) => (
              <div key={i} className="card" style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{repo.name}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                      <code style={{ fontFamily: 'var(--mono)' }}>{repo.url}</code>
                    </div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                      <span className="tag">branch: {repo.branch}</span>
                    </div>
                  </div>
                  <div className="badge badge-green">● Active</div>
                </div>
              </div>
            ))}

            <div className="section-label" style={{ marginTop: 24 }}>Link GitHub Repository</div>
            <div className="card">
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  style={{ flex: 1, background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '8px 12px', color: 'var(--text-primary)', fontSize: 13, outline: 'none' }}
                  placeholder="https://github.com/user/repo"
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                />
                <button className="btn btn-secondary" onClick={() => { if (repoUrl) setLinked(true); }}>
                  Link
                </button>
              </div>
              {linked && <div className="badge badge-green" style={{ marginTop: 10 }}>✓ Repository linked to graph</div>}
            </div>
          </div>

          <div>
            <div className="section-label">Environment Configuration</div>
            <div className="card">
              {ENV_VARS.map((v, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: i < ENV_VARS.length - 1 ? '1px solid var(--border-subtle)' : 'none' }}>
                  <div>
                    <code style={{ fontSize: 12, color: 'var(--cyan)' }}>{v.key}</code>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{v.value}</span>
                    <div className={`badge ${v.status === 'set' ? 'badge-green' : 'badge-amber'}`}>
                      {v.status}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="section-label" style={{ marginTop: 24 }}>Platform Adapters</div>
            <div className="card">
              {['ChatGPT', 'Claude', 'Gemini', 'Localhost'].map((platform) => (
                <div key={platform} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: 13 }}>{platform}</span>
                  <div className="badge badge-green">✓ Active</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
