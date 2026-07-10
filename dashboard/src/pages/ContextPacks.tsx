import { useState } from 'react';
import { api, type CompileResponse } from '../api';

type Role = 'backend' | 'frontend' | 'devops' | 'bugfix';

const PACKS: { id: Role; label: string; emoji: string; color: string; sections: { key: string; label: string; desc: string }[] }[] = [
  {
    id: 'backend', label: 'Backend Pack', emoji: '⚙️', color: 'var(--accent)',
    sections: [
      { key: 'architecture', label: 'Architecture.md', desc: 'System components and interactions' },
      { key: 'apis', label: 'APIs.md', desc: 'Endpoint decisions and route specs' },
      { key: 'database', label: 'Database.md', desc: 'Neo4j schema and data models' },
      { key: 'constraints', label: 'Constraints.md', desc: 'Technical limits and performance SLAs' },
    ],
  },
  {
    id: 'frontend', label: 'Frontend Pack', emoji: '🎨', color: 'var(--cyan)',
    sections: [
      { key: 'architecture', label: 'Architecture.md', desc: 'Component structure' },
      { key: 'coding_style', label: 'CodingStyle.md', desc: 'TypeScript and Tailwind rules' },
      { key: 'constraints', label: 'Constraints.md', desc: 'Performance and UX constraints' },
      { key: 'current_progress', label: 'Progress.md', desc: 'Completed and in-progress features' },
    ],
  },
  {
    id: 'devops', label: 'DevOps Pack', emoji: '🐳', color: 'var(--green)',
    sections: [
      { key: 'constraints', label: 'Constraints.md', desc: 'Infrastructure limits' },
      { key: 'architecture', label: 'Architecture.md', desc: 'Service topology' },
      { key: 'database', label: 'Database.md', desc: 'Neo4j AuraDB config' },
    ],
  },
  {
    id: 'bugfix', label: 'Bug Fix Pack', emoji: '🐛', color: 'var(--amber)',
    sections: [
      { key: 'current_progress', label: 'Progress.md', desc: 'Known state at last checkpoint' },
      { key: 'tasks', label: 'Tasks.md', desc: 'Pending action items' },
      { key: 'constraints', label: 'Constraints.md', desc: 'System constraints to respect' },
    ],
  },
];

export default function ContextPacks() {
  const [selectedRole, setSelectedRole] = useState<Role>('backend');
  const [selections, setSelections] = useState<Record<string, boolean>>({
    architecture: true, apis: true, database: true, constraints: true,
    coding_style: true, current_progress: true, tasks: true,
  });
  const [compiled, setCompiled] = useState<CompileResponse | null>(null);
  const [compiling, setCompiling] = useState(false);
  const [copied, setCopied] = useState(false);

  const activePack = PACKS.find((p) => p.id === selectedRole)!;

  const handleCompile = async () => {
    setCompiling(true);
    setCompiled(null);
    try {
      const result = await api.compile({
        conversation_id: 'conv_mock_001',
        role_pack: selectedRole,
        selections,
      });
      setCompiled(result);
    } catch {
      // Backend offline — create mock
      const files: Record<string, string> = {};
      activePack.sections.filter((s) => selections[s.key]).forEach((s) => {
        files[s.label] = `# ${s.label.replace('.md', '')}\n\nCompiled from ContextOS Project Memory.\n\n> This file was auto-generated. Connect to backend for live data.`;
      });
      setCompiled({ pack_id: 'pack_local', role_pack: selectedRole, files });
    } finally {
      setCompiling(false);
    }
  };

  const handleCopy = () => {
    if (!compiled) return;
    const content = Object.entries(compiled.files)
      .map(([name, body]) => `## ${name}\n\n${body}`)
      .join('\n\n---\n\n');
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <div className="page-title">Context Packs</div>
        <div className="page-subtitle">Compile role-specific Smart Packs from your Project Memory.</div>
      </div>

      <div className="page-content">
        <div className="grid-2" style={{ alignItems: 'flex-start' }}>
          {/* Left: Pack selector + options */}
          <div>
            <div className="section-label">Select Pack Role</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 24 }}>
              {PACKS.map((pack) => (
                <div
                  key={pack.id}
                  className="card"
                  style={{
                    cursor: 'pointer',
                    borderColor: selectedRole === pack.id ? pack.color : 'var(--border)',
                    background: selectedRole === pack.id ? pack.color + '11' : 'var(--bg-surface)',
                    transition: 'all 0.2s',
                  }}
                  onClick={() => { setSelectedRole(pack.id); setCompiled(null); }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ fontSize: 20 }}>{pack.emoji}</span>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: selectedRole === pack.id ? pack.color : 'var(--text-primary)' }}>
                        {pack.label}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                        {pack.sections.length} sections
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="section-label">Configure Sections</div>
            {activePack.sections.map((section) => (
              <label key={section.key} className="check-item" htmlFor={`chk-${section.key}`}>
                <input
                  type="checkbox" id={`chk-${section.key}`}
                  checked={selections[section.key] ?? false}
                  onChange={(e) => setSelections((s) => ({ ...s, [section.key]: e.target.checked }))}
                />
                <div className="check-label">
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{section.label}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{section.desc}</div>
                </div>
              </label>
            ))}

            <button
              className="btn btn-primary"
              style={{ width: '100%', marginTop: 16, justifyContent: 'center' }}
              onClick={handleCompile}
              disabled={compiling}
            >
              {compiling ? '⟳ Compiling...' : `📦 Compile ${activePack.label}`}
            </button>
          </div>

          {/* Right: Compiled output */}
          <div>
            {compiled ? (
              <div className="fade-in">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div className="section-label" style={{ margin: 0 }}>Compiled Output</div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-secondary" onClick={handleCopy}>
                      {copied ? '✓ Copied!' : '📋 Copy All'}
                    </button>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {Object.entries(compiled.files).map(([filename, content]) => (
                    <div key={filename} className="card">
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <div className="card-title" style={{ margin: 0 }}>{filename}</div>
                        <div className="badge badge-green">✓ Ready</div>
                      </div>
                      <div className="code-block" style={{ maxHeight: 160, overflowY: 'auto', fontSize: 11 }}>
                        {content}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="citation" style={{ marginTop: 16 }}>
                  <strong>Paste into:</strong> Cursor → <code>.cursorrules</code> · VS Code → <code>.context/</code> · ChatGPT → System Prompt
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <div className="empty-state-icon">📦</div>
                <div className="empty-state-title">No Pack Compiled Yet</div>
                <div className="empty-state-sub">Select a role and click Compile to generate your Smart Pack.</div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
