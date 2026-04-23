import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import clsx from 'clsx'
import SourceCard from './SourceCard'

const ThinkingDots = () => (
  <span className="flex gap-1 items-center h-5">
    {[0, 0.15, 0.3].map(d => (
      <span
        key={d}
        className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse-dot"
        style={{ animationDelay: `${d}s` }}
      />
    ))}
  </span>
)

const CodeBlock = ({ inline, className, children }) => {
  const match = /language-(\w+)/.exec(className || '')
  return !inline && match ? (
    <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div">
      {String(children).replace(/\n$/, '')}
    </SyntaxHighlighter>
  ) : (
    <code className={className}>{children}</code>
  )
}

export default function ChatMessage({ msg }) {
  const isUser = msg.role === 'user'

  return (
    <div className={clsx('flex gap-3 animate-slide-up', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-brand-500 to-purple-500
                        flex items-center justify-center text-white text-xs font-bold shadow-sm">
          AI
        </div>
      )}

      <div className={clsx(
        'max-w-[80%] rounded-2xl px-4 py-3 shadow-sm',
        isUser
          ? 'bg-brand-500 text-white rounded-tr-sm'
          : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-tl-sm'
      )}>
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        ) : (
          <>
            {msg.streaming && !msg.content ? (
              <ThinkingDots />
            ) : (
              <div className="prose-rag text-sm">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{ code: CodeBlock }}
                >
                  {msg.content}
                </ReactMarkdown>
                {msg.streaming && <ThinkingDots />}
              </div>
            )}

            {!msg.streaming && (
              <>
                <SourceCard sources={msg.sources} />
                {(msg.latency || msg.fromCache) && (
                  <p className="text-[10px] text-gray-400 dark:text-gray-600 mt-2">
                    {msg.fromCache ? '⚡ cached' : `${msg.latency}ms`}
                  </p>
                )}
              </>
            )}

            {msg.error && (
              <p className="text-xs text-red-500 mt-1">Something went wrong. Please try again.</p>
            )}
          </>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700
                        flex items-center justify-center text-gray-600 dark:text-gray-400 text-xs font-bold">
          You
        </div>
      )}
    </div>
  )
}
