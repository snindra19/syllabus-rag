import { useEffect, useRef, useState } from 'react'
import { streamChat } from '../api/client'
import MessageBubble from './MessageBubble'

export default function ChatWindow({ selectedIds }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const abortRef = useRef(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSubmit(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || busy) return

    setInput('')
    setBusy(true)

    setMessages(prev => [
      ...prev,
      { role: 'user', text },
      { role: 'assistant', text: '', streaming: true },
    ])

    abortRef.current = streamChat(text, selectedIds, {
      onToken(token) {
        setMessages(prev => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last?.role === 'assistant') {
            next[next.length - 1] = { ...last, text: last.text + token }
          }
          return next
        })
      },
      onDone() {
        setMessages(prev => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last?.role === 'assistant') {
            next[next.length - 1] = { ...last, streaming: false }
          }
          return next
        })
        setBusy(false)
      },
      onError(err) {
        setMessages(prev => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last?.role === 'assistant') {
            next[next.length - 1] = {
              ...last,
              text: `Error: ${err.message}`,
              streaming: false,
            }
          }
          return next
        })
        setBusy(false)
      },
    })
  }

  function handleStop() {
    abortRef.current?.abort()
    setBusy(false)
    setMessages(prev => {
      const next = [...prev]
      const last = next[next.length - 1]
      if (last?.role === 'assistant') {
        next[next.length - 1] = { ...last, streaming: false }
      }
      return next
    })
  }

  return (
    // flex-1 + min-h-0 let this column fill remaining space without overflowing
    <div className="flex-1 flex flex-col min-h-0">

      {/* Scrollable message thread — the only overflowing region */}
      <div className="flex-1 overflow-y-auto min-h-0 px-4 py-4 bg-gray-50 dark:bg-gray-900">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 dark:text-gray-600 select-none">
            <svg className="w-12 h-12 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-4 4v-4z" />
            </svg>
            <p className="text-sm">Ask a question about your syllabus</p>
            {selectedIds.length === 0 && (
              <p className="text-xs mt-1">Upload a syllabus or select one in the sidebar</p>
            )}
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} text={msg.text} streaming={msg.streaming} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Fixed input bar — never scrolls away */}
      <form
        onSubmit={handleSubmit}
        className="flex-shrink-0 flex gap-2 px-4 py-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700"
      >
        <input
          className="flex-1 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          placeholder={selectedIds.length > 0
            ? 'Ask about the selected syllabus…'
            : 'Ask about any uploaded syllabus…'}
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={busy}
        />
        {busy ? (
          <button
            type="button"
            onClick={handleStop}
            className="px-4 py-2 rounded-xl bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400 text-sm font-medium hover:bg-red-200 dark:hover:bg-red-900/60 transition-colors"
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim()}
            className="px-4 py-2 rounded-xl bg-amber-500 text-white text-sm font-medium hover:bg-amber-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        )}
      </form>
    </div>
  )
}
