import { useState, useRef, useCallback, useEffect } from 'react'
import { createStream, queryRag } from '../utils/api'
import { v4 as uuidv4 } from 'uuid'

const SESSION_ID = uuidv4()

export function useChat(docFilter) {
  const [messages, setMessages] = useState([])
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState(null)
  const wsRef = useRef(null)
  const streamingIdRef = useRef(null)

  const history = messages
    .filter(m => m.role !== 'system')
    .slice(-10)
    .map(m => ({ role: m.role, content: m.content }))

  const addMessage = useCallback((msg) => {
    setMessages(prev => [...prev, { id: uuidv4(), timestamp: Date.now(), ...msg }])
  }, [])

  const updateLastAssistant = useCallback((updater) => {
    setMessages(prev => {
      const copy = [...prev]
      const last = copy.findLastIndex(m => m.role === 'assistant')
      if (last >= 0) copy[last] = { ...copy[last], ...updater(copy[last]) }
      return copy
    })
  }, [])

  const sendMessage = useCallback(async (question) => {
    if (streaming || !question.trim()) return
    setError(null)

    addMessage({ role: 'user', content: question })

    const assistantId = uuidv4()
    streamingIdRef.current = assistantId
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      content: '',
      sources: [],
      streaming: true,
      timestamp: Date.now(),
    }])
    setStreaming(true)

    // Prefer WebSocket streaming; fallback to REST
    try {
      if (!wsRef.current || wsRef.current.readyState > 1) {
        wsRef.current = createStream(
          (sources) => {
            setMessages(prev => prev.map(m =>
              m.id === streamingIdRef.current ? { ...m, sources } : m
            ))
          },
          (token) => {
            setMessages(prev => prev.map(m =>
              m.id === streamingIdRef.current
                ? { ...m, content: m.content + token }
                : m
            ))
          },
          () => {
            setMessages(prev => prev.map(m =>
              m.id === streamingIdRef.current ? { ...m, streaming: false } : m
            ))
            setStreaming(false)
          },
          (errMsg) => {
            setError(errMsg)
            setMessages(prev => prev.map(m =>
              m.id === streamingIdRef.current ? { ...m, streaming: false, error: true } : m
            ))
            setStreaming(false)
          }
        )

        // Wait for ws open
        await new Promise((res, rej) => {
          wsRef.current.onopen = res
          setTimeout(() => rej(new Error('WS timeout')), 5000)
        })
      }

      wsRef.current.send(JSON.stringify({
        question,
        doc_filter: docFilter || null,
        history,
        session_id: SESSION_ID,
      }))

    } catch {
      // WebSocket failed — fall back to REST
      try {
        const data = await queryRag(question, {
          docFilter,
          history,
          sessionId: SESSION_ID,
        })
        setMessages(prev => prev.map(m =>
          m.id === assistantId
            ? { ...m, content: data.answer, sources: data.sources, streaming: false,
                latency: data.latency_ms, fromCache: data.from_cache }
            : m
        ))
      } catch (e) {
        setError(e.response?.data?.detail || 'Query failed. Please try again.')
        setMessages(prev => prev.map(m =>
          m.id === assistantId ? { ...m, streaming: false, error: true } : m
        ))
      } finally {
        setStreaming(false)
      }
    }
  }, [streaming, docFilter, history, addMessage])

  const clearChat = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])

  // Close WS on unmount
  useEffect(() => () => wsRef.current?.close(), [])

  return { messages, streaming, error, sendMessage, clearChat }
}
