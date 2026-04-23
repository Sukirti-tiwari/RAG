import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// ── Documents ─────────────────────────────────────────────────────
export const uploadFile = (file, onProgress) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total)),
  })
}

export const ingestUrl = (url, name) =>
  api.post('/ingest-url', { url, name })

export const listDocuments = () =>
  api.get('/documents').then(r => r.data)

export const getDocStatus = id =>
  api.get(`/documents/${id}/status`).then(r => r.data)

export const deleteDocument = id =>
  api.delete(`/documents/${id}`)

// ── Query ─────────────────────────────────────────────────────────
export const queryRag = (question, { docFilter, history, sessionId, useCache = true } = {}) =>
  api.post('/query', {
    question,
    doc_filter: docFilter || null,
    history: history || [],
    session_id: sessionId,
    use_cache: useCache,
  }).then(r => r.data)

// ── WebSocket stream ──────────────────────────────────────────────
export function createStream(onSources, onToken, onDone, onError) {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  const host = window.location.host
  const ws = new WebSocket(`${protocol}://${host}/api/ws/stream`)

  ws.onmessage = e => {
    const msg = JSON.parse(e.data)
    if (msg.type === 'sources') onSources(msg.data)
    else if (msg.type === 'token') onToken(msg.data)
    else if (msg.type === 'done') onDone()
    else if (msg.type === 'error') onError(msg.data)
  }

  ws.onerror = () => onError('WebSocket connection failed')

  return ws
}

export default api
