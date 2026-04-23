import { useEffect, useRef, useState } from 'react'
import clsx from 'clsx'
import ChatMessage from './ChatMessage'

const SUGGESTIONS = [
  'Summarize the main points of the uploaded documents',
  'What are the key findings?',
  'Explain the methodology used',
  'List all the important dates and events',
]

export default function ChatWindow({ messages, streaming, error, onSend, onClear, selectedDoc }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  const handleSend = () => {
    const q = input.trim()
    if (!q || streaming) return
    onSend(q)
    setInput('')
    textareaRef.current?.focus()
  }

  const handleKey = e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
        <div>
          <h2 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">
            Chat
            {selectedDoc && (
              <span className="ml-2 text-[10px] font-normal px-1.5 py-0.5 bg-brand-100 dark:bg-brand-900/30
                               text-brand-600 dark:text-brand-400 rounded-full">
                filtered
              </span>
            )}
          </h2>
          <p className="text-xs text-gray-400 dark:text-gray-600">
            {selectedDoc ? 'Searching selected document' : 'Searching all documents'}
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={onClear}
            className="text-xs text-gray-400 hover:text-red-500 transition-colors px-2 py-1 rounded"
          >
            Clear chat
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-4">
            <div className="text-5xl">🔍</div>
            <div>
              <h3 className="text-base font-semibold text-gray-700 dark:text-gray-300">
                Ask anything about your documents
              </h3>
              <p className="text-sm text-gray-400 mt-1">
                Upload documents on the left, then ask questions here
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2 w-full max-w-sm mt-2">
              {SUGGESTIONS.map(s => (
                <button
                  key={s}
                  onClick={() => onSend(s)}
                  className="text-left text-xs px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700
                             hover:border-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20
                             text-gray-600 dark:text-gray-400 transition-all"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map(msg => <ChatMessage key={msg.id} msg={msg} />)
        )}
        {error && (
          <div className="flex justify-center">
            <p className="text-xs text-red-500 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg">
              {error}
            </p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-800 p-4">
        <div className={clsx(
          'flex gap-2 items-end bg-white dark:bg-gray-800 border rounded-xl p-2 transition-all',
          'focus-within:ring-2 focus-within:ring-brand-500 focus-within:border-transparent',
          'border-gray-200 dark:border-gray-700 shadow-sm'
        )}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask a question about your documents…"
            rows={1}
            disabled={streaming}
            className="flex-1 resize-none bg-transparent text-sm text-gray-900 dark:text-gray-100
                       placeholder:text-gray-400 focus:outline-none max-h-32 overflow-y-auto
                       disabled:opacity-50"
            style={{ fieldSizing: 'content' }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || streaming}
            className={clsx(
              'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all',
              input.trim() && !streaming
                ? 'bg-brand-500 text-white hover:bg-brand-600 shadow-sm'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
            )}
          >
            {streaming ? (
              <span className="w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" viewBox="0 0 16 16" fill="currentColor">
                <path d="M1.5 1.5l13 6.5-13 6.5v-5l9-1.5-9-1.5z"/>
              </svg>
            )}
          </button>
        </div>
        <p className="text-[10px] text-gray-400 mt-1.5 text-center">
          Enter to send · Shift+Enter for newline
        </p>
      </div>
    </div>
  )
}
