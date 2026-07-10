import { useState } from 'react';
import Overview from './pages/Overview';
import Projects from './pages/Projects';
import Timeline from './pages/Timeline';
import KnowledgeGraph from './pages/KnowledgeGraph';
import ContextPacks from './pages/ContextPacks';
import ExportCenter from './pages/ExportCenter';

type Page = 'overview' | 'projects' | 'timeline' | 'graph' | 'packs' | 'export';

const NAV: { id: Page; label: string; icon: string }[] = [
  { id: 'overview',  label: 'Overview',        icon: '⬡' },
  { id: 'projects',  label: 'Projects',         icon: '◫' },
  { id: 'timeline',  label: 'Timeline',         icon: '◷' },
  { id: 'graph',     label: 'Knowledge Graph',  icon: '⬡' },
  { id: 'packs',     label: 'Context Packs',    icon: '◈' },
  { id: 'export',    label: 'Export Center',    icon: '↗' },
];

export default function App() {
  const [page, setPage] = useState<Page>('overview');

  const renderPage = () => {
    switch (page) {
      case 'overview':  return <Overview onNavigate={setPage} />;
      case 'projects':  return <Projects />;
      case 'timeline':  return <Timeline />;
      case 'graph':     return <KnowledgeGraph />;
      case 'packs':     return <ContextPacks />;
      case 'export':    return <ExportCenter />;
    }
  };

  return (
    <div className="layout">
      {/* Sidebar */}
      <nav className="sidebar">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">⬡</div>
          <span className="sidebar-logo-text">ContextOS</span>
        </div>

        {NAV.map((item) => (
          <button
            key={item.id}
            className={`nav-item ${page === item.id ? 'active' : ''}`}
            onClick={() => setPage(item.id)}
          >
            <span style={{ fontSize: 16 }}>{item.icon}</span>
            {item.label}
          </button>
        ))}

      </nav>

      {/* Main Content */}
      <main className="main">{renderPage()}</main>
    </div>
  );
}
