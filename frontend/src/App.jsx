import { useState, useEffect } from 'react'
import FileUploader from './components/FileUploader'
import DocumentList from './components/DocumentList'
import ChatWindow from './components/ChatWindow'
import { useDocuments } from './hooks/useDocuments'
import { useChat } from './hooks/useChat'
import clsx from 'clsx'

function ThemeToggle({ dark, toggle }) {
  return (
    <button
      onClick={toggle}
      className="w-8 h-8 flex items-center justify-center rounded-lg
                 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      title={dark ? 'Light mode' : 'Dark mode'}
    >
      {dark ? '☀️' : '🌙'}
    </button>
  )
}

export default function App() {
  const [dark, setDark] = useState(() =>
    window.matchMedia('(prefers-color-scheme: dark)').matches
  )
  const [selectedDoc, setSelectedDoc] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const { docs, loading, upload, addUrl, remove } = useDocuments()
  const { messages, streaming, error, sendMessage, clearChat } = useChat(selectedDoc)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
  }, [dark])

  const readyDocs = docs.filter(d => d.status === 'ready')

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Top nav */}
      <header className="flex items-center gap-3 px-4 py-2.5 bg-white dark:bg-gray-900
                         border-b border-gray-200 dark:border-gray-800 flex-shrink-0 shadow-sm">
        <button
          onClick={() => setSidebarOpen(s => !s)}
          className="w-8 h-8 flex items-center justify-center rounded-lg
                     text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          ☰
        </button>
        <div className="flex items-center gap-2">
          <span className="text-lg">🔬</span>
          <h1 className="font-bold text-gray-900 dark:text-gray-100">RAG Intelligence</h1>
          <span className="text-[10px] px-1.5 py-0.5 bg-brand-100 dark:bg-brand-900/40
                           text-brand-600 dark:text-brand-400 rounded font-medium">
            v1.0
          </span>
        </div>
        <div className="flex-1" />
        <div className="hidden sm:flex items-center gap-3 text-xs text-gray-400">
          <span>{readyDocs.length} doc{readyDocs.length !== 1 ? 's' : ''} indexed</span>
          <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
        </div>
        <ThemeToggle dark={dark} toggle={() => setDark(d => !d)} />
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className={clsx(
          'flex flex-col bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800',
          'transition-all duration-200 flex-shrink-0 overflow-hidden',
          sidebarOpen ? 'w-72' : 'w-0'
        )}>
          <div className="flex flex-col h-full overflow-hidden w-72">
            {/* Upload */}
            <div className="p-4 border-b border-gray-100 dark:border-gray-800 flex-shrink-0">
              <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase
                             tracking-wider mb-3">
                Knowledge Base
              </h2>
              <FileUploader
                onUpload={upload}
                onUrlAdd={addUrl}
                loading={loading}
              />
            </div>

            {/* Document list */}
            <div className="flex-1 overflow-y-auto p-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Documents
                </h2>
                {selectedDoc && (
                  <button
                    onClick={() => setSelectedDoc(null)}
                    className="text-[10px] text-brand-500 hover:text-brand-600"
                  >
                    Clear filter
                  </button>
                )}
              </div>
              <DocumentList
                docs={docs}
                selectedId={selectedDoc}
                onSelect={setSelectedDoc}
                onDelete={remove}
              />
            </div>

            {/* Stats footer */}
            {readyDocs.length > 0 && (
              <div className="p-3 border-t border-gray-100 dark:border-gray-800 flex-shrink-0">
                <div className="grid grid-cols-3 gap-2 text-center">
                  {[
                    { label: 'Docs', value: readyDocs.length },
                    { label: 'Chunks', value: readyDocs.reduce((a, d) => a + (d.chunks || 0), 0) },
                    { label: 'Msgs', value: messages.filter(m => m.role === 'user').length },
                  ].map(stat => (
                    <div key={stat.label} className="bg-gray-50 dark:bg-gray-800 rounded-lg p-2">
                      <p className="text-sm font-bold text-gray-900 dark:text-gray-100">{stat.value}</p>
                      <p className="text-[10px] text-gray-400">{stat.label}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </aside>

        {/* Chat */}
        <main className="flex-1 overflow-hidden">
          <ChatWindow
            messages={messages}
            streaming={streaming}
            error={error}
            onSend={sendMessage}
            onClear={clearChat}
            selectedDoc={selectedDoc}
          />
        </main>
      </div>
    </div>
  )
}
