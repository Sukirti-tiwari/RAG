import clsx from 'clsx'

const STATUS_COLORS = {
  ready:      'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
  processing: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400',
  error:      'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
}

const FILE_ICONS = {
  pdf: '📕', docx: '📘', xlsx: '📗', csv: '📊',
  html: '🌐', txt: '📄', url: '🔗',
}

function fmt(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / 1048576).toFixed(1) + 'MB'
}

export default function DocumentList({ docs, selectedId, onSelect, onDelete }) {
  if (!docs.length) {
    return (
      <div className="text-center py-8 text-gray-400 dark:text-gray-600">
        <div className="text-4xl mb-2">📂</div>
        <p className="text-sm">No documents yet</p>
        <p className="text-xs mt-1">Upload files above to get started</p>
      </div>
    )
  }

  return (
    <ul className="space-y-1.5">
      {docs.map(doc => (
        <li key={doc.id}>
          <div
            onClick={() => doc.status === 'ready' && onSelect(doc.id === selectedId ? null : doc.id)}
            className={clsx(
              'group flex items-start gap-2.5 p-2.5 rounded-lg cursor-pointer transition-all',
              doc.status !== 'ready' && 'cursor-default opacity-70',
              doc.id === selectedId
                ? 'bg-brand-50 dark:bg-brand-900/30 ring-1 ring-brand-500/40'
                : 'hover:bg-gray-50 dark:hover:bg-gray-800/60'
            )}
          >
            <span className="text-lg flex-shrink-0 mt-0.5">
              {FILE_ICONS[doc.type] || '📄'}
            </span>
            <div className="flex-1 min-w-0">
              <p className={clsx(
                'text-sm font-medium truncate',
                doc.id === selectedId
                  ? 'text-brand-700 dark:text-brand-300'
                  : 'text-gray-800 dark:text-gray-200'
              )}>
                {doc.name}
              </p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className={clsx(
                  'text-[10px] font-medium px-1.5 py-0.5 rounded-full',
                  STATUS_COLORS[doc.status] || STATUS_COLORS.processing
                )}>
                  {doc.status}
                </span>
                {doc.status === 'ready' && (
                  <span className="text-[10px] text-gray-400">
                    {doc.chunks} chunks
                    {doc.size ? ` · ${fmt(doc.size)}` : ''}
                  </span>
                )}
                {doc.status === 'processing' && (
                  <span className="flex gap-0.5">
                    {[0, 0.2, 0.4].map(d => (
                      <span
                        key={d}
                        className="w-1 h-1 bg-yellow-400 rounded-full animate-pulse-dot"
                        style={{ animationDelay: `${d}s` }}
                      />
                    ))}
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={e => { e.stopPropagation(); onDelete(doc.id) }}
              className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500
                         transition-all p-0.5 rounded flex-shrink-0"
              title="Delete"
            >
              ×
            </button>
          </div>
        </li>
      ))}
    </ul>
  )
}
