import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import clsx from 'clsx'

const ACCEPTED = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'text/csv': ['.csv'],
  'text/html': ['.html'],
  'text/plain': ['.txt', '.md'],
}

export default function FileUploader({ onUpload, onUrlAdd, loading }) {
  const [urlInput, setUrlInput] = useState('')
  const [urlName, setUrlName] = useState('')
  const [tab, setTab] = useState('file') // 'file' | 'url'
  const [progress, setProgress] = useState(null)
  const [dragError, setDragError] = useState('')

  const onDrop = useCallback(async (accepted, rejected) => {
    setDragError('')
    if (rejected.length) {
      setDragError(`Unsupported file type: ${rejected[0].file.name}`)
      return
    }
    for (const file of accepted) {
      setProgress(0)
      await onUpload(file, p => setProgress(p))
      setProgress(null)
    }
  }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    multiple: true,
    disabled: loading,
  })

  const handleUrl = async () => {
    if (!urlInput.trim()) return
    await onUrlAdd(urlInput.trim(), urlName.trim() || undefined)
    setUrlInput('')
    setUrlName('')
  }

  return (
    <div className="space-y-3">
      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
        {['file', 'url'].map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={clsx(
              'flex-1 py-1.5 text-sm rounded-md font-medium transition-all',
              tab === t
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700'
            )}
          >
            {t === 'file' ? '📄 File' : '🔗 URL'}
          </button>
        ))}
      </div>

      {tab === 'file' ? (
        <div
          {...getRootProps()}
          className={clsx(
            'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all',
            isDragActive
              ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20'
              : 'border-gray-200 dark:border-gray-700 hover:border-brand-400 hover:bg-gray-50 dark:hover:bg-gray-800/50',
            loading && 'opacity-50 cursor-not-allowed'
          )}
        >
          <input {...getInputProps()} />
          <div className="text-3xl mb-2">
            {isDragActive ? '📥' : '☁️'}
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {isDragActive ? 'Drop to upload' : 'Drag files here or click to browse'}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            PDF, DOCX, XLSX, CSV, HTML, TXT
          </p>
          {progress !== null && (
            <div className="mt-3">
              <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-500 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">{progress}%</p>
            </div>
          )}
          {dragError && (
            <p className="text-xs text-red-500 mt-2">{dragError}</p>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <input
            type="url"
            value={urlInput}
            onChange={e => setUrlInput(e.target.value)}
            placeholder="https://example.com/document"
            className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700
                       rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                       focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
          <input
            type="text"
            value={urlName}
            onChange={e => setUrlName(e.target.value)}
            placeholder="Display name (optional)"
            className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-700
                       rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                       focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            onClick={handleUrl}
            disabled={!urlInput.trim() || loading}
            className="w-full py-2 text-sm font-medium bg-brand-500 text-white rounded-lg
                       hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Ingesting...' : 'Ingest URL'}
          </button>
        </div>
      )}
    </div>
  )
}
