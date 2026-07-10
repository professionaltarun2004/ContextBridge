// ContextOS Dashboard — API Client
// Communicates with the FastAPI backend

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export interface ImportRequest {
  platform: string;
  url: string;
  messages: { id: string; role: string; text: string; timestamp: string }[];
}
export interface ImportResponse {
  status: string;
  conversation_id: string;
  nodes_extracted: number;
  relationships_created: number;
  execution_time_ms: number;
}

export interface GraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}
export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
}
export interface GraphResponse { nodes: GraphNode[]; edges: GraphEdge[]; }

export interface CompileRequest {
  conversation_id: string;
  role_pack: 'backend' | 'frontend' | 'devops' | 'bugfix';
  selections: Record<string, boolean>;
}
export interface CompileResponse {
  pack_id: string;
  role_pack: string;
  files: Record<string, string>;
}

export interface PackSummary { pack_id: string; role_pack: string; created_at: string; }
export interface PacksResponse { packs: PackSummary[]; }

export interface AskResponse {
  answer: string;
  confidence_average: number;
  citations: { node_id: string; node_label: string; source_message: string; source_ai: string; conversation_id: string }[];
}

export const api = {
  import: (data: ImportRequest) =>
    request<ImportResponse>('/api/v1/import', { method: 'POST', body: JSON.stringify(data) }),

  graph: (conversation_id?: string) =>
    request<GraphResponse>(`/api/v1/graph${conversation_id ? `?conversation_id=${conversation_id}` : ''}`),

  compile: (data: CompileRequest) =>
    request<CompileResponse>('/api/v1/compile', { method: 'POST', body: JSON.stringify(data) }),

  packs: () => request<PacksResponse>('/api/v1/packs'),

  export: (pack_id: string, format = 'zip') =>
    request<{ download_url: string }>('/api/v1/export', { method: 'POST', body: JSON.stringify({ pack_id, format }) }),

  ask: (question: string) =>
    request<AskResponse>('/api/v1/ask', { method: 'POST', body: JSON.stringify({ question }) }),
};
