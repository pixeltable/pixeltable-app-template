import type {
  QueryResponse,
  FilesResponse,
  ChunksResponse,
  FramesResponse,
  TranscriptionResponse,
  SearchResponse,
  Conversation,
  ChatMessage,
} from '@/types'

const BASE = '/api'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? body.error ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

// ── Data ─────────────────────────────────────────────────────────────────────

export async function uploadFile(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${BASE}/data/upload`, { method: 'POST', body: formData })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(body.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getFiles(): Promise<FilesResponse> {
  return request<FilesResponse>(`${BASE}/data/files`)
}

export async function deleteFile(uuid: string, type: string) {
  return request<{ message: string }>(`${BASE}/data/files/${uuid}/${type}`, { method: 'DELETE' })
}

export async function getChunks(uuid: string): Promise<ChunksResponse> {
  return request<ChunksResponse>(`${BASE}/data/chunks/${uuid}`)
}

export async function getFrames(uuid: string): Promise<FramesResponse> {
  return request<FramesResponse>(`${BASE}/data/frames/${uuid}`)
}

export async function getTranscription(uuid: string): Promise<TranscriptionResponse> {
  return request<TranscriptionResponse>(`${BASE}/data/transcription/${uuid}`)
}

// ── Search ───────────────────────────────────────────────────────────────────

export async function search(params: {
  query: string
  types?: string[]
  limit?: number
}): Promise<SearchResponse> {
  return request<SearchResponse>(`${BASE}/search`, {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

// ── Agent ────────────────────────────────────────────────────────────────────

export async function sendQuery(
  query: string,
  conversationId?: string | null,
): Promise<QueryResponse> {
  return request<QueryResponse>(`${BASE}/agent/query`, {
    method: 'POST',
    body: JSON.stringify({ query, conversation_id: conversationId }),
  })
}

export async function getConversations(): Promise<Conversation[]> {
  return request<Conversation[]>(`${BASE}/agent/conversations`)
}

export async function getConversation(
  id: string,
): Promise<{ conversation_id: string; messages: ChatMessage[] }> {
  return request(`${BASE}/agent/conversations/${encodeURIComponent(id)}`)
}

export async function deleteConversation(id: string) {
  return request<{ message: string }>(
    `${BASE}/agent/conversations/${encodeURIComponent(id)}`,
    { method: 'DELETE' },
  )
}
