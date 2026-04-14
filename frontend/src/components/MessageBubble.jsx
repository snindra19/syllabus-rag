/**
 * A single chat message bubble.
 * role: 'user' | 'assistant'
 * text: string
 * streaming: bool — true while tokens are arriving
 *
 * States:
 *  streaming=true, text=''  → typing indicator (three bouncing dots)
 *  streaming=true, text≠''  → text + blinking cursor
 *  streaming=false          → static text
 */
export default function MessageBubble({ role, text, streaming = false }) {
  const isUser = role === 'user'
  const isTyping = streaming && !text

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      {!isUser && (
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-amber-500 flex items-center justify-center text-white text-xs font-bold mr-2 mt-1">
          AI
        </div>
      )}

      <div
        className={`
          max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap
          ${isUser
            ? 'bg-amber-500 text-white rounded-tr-sm'
            : 'bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-800 dark:text-gray-100 rounded-tl-sm shadow-sm'
          }
        `}
      >
        {isTyping ? (
          /* Three bouncing dots — typing indicator */
          <span className="flex items-center gap-1 h-4">
            <span className="w-1.5 h-1.5 rounded-full bg-current animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-current animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-current animate-bounce" style={{ animationDelay: '300ms' }} />
          </span>
        ) : (
          <>
            {text}
            {streaming && (
              <span className="inline-block w-1.5 h-4 bg-current ml-0.5 align-middle animate-pulse" />
            )}
          </>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gray-300 dark:bg-gray-600 flex items-center justify-center text-gray-600 dark:text-gray-300 text-xs font-bold ml-2 mt-1">
          You
        </div>
      )}
    </div>
  )
}
