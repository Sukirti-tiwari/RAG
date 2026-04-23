import { useState } from 'react'
import clsx from 'clsx'

export default function SourceCard({ sources }) {
  const [expanded, setExpanded] = useState(false)
  const [openIdx, setOpenIdx] = useState(null)

  if (!sources?.length) return null

  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded(e => !e)}
        className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400
                   hover:text-brand-500 transition-colors"
      >
        <span className={clsx('transition-transform duration-200', expanded ? 'rotate-90' : '')}>▶</span>
        {sources.length} source{sources.length > 1 ? 's' : ''}
      </button>

      {expanded && (
        <div className="mt-2 space-y-1.5 animate-fade-in">
          {sources.map((src, i) => (
            <div
              key={i}
              className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
            >
              <button
                onClick={() => setOpenIdx(openIdx === i ? null : i)}
                className="w-full flex items-center gap-2 px-3 py-2 text-left
                           hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
              >
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-brand-500 text-white
                                 text-[10px] font-bold flex items-center justify-center">
                  {src.citation}
                </span>
                <span className="flex-1 text-xs text-gray-600 dark:text-gray-400 truncate">
                  {src.page ? `Page ${src.page} · ` : ''}
                  {src.content.substring(0, 80)}…
                </span>
                <span className="flex-shrink-0 text-[10px] text-gray-400">
                  {src.score ? (src.score * 100).toFixed(0) + '%' : ''}
                </span>
              </button>
              {openIdx === i && (
                <div className="px-3 py-2.5 bg-gray-50 dark:bg-gray-800/30 border-t
                                border-gray-200 dark:border-gray-700 animate-fade-in">
                  <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                    {src.content}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
