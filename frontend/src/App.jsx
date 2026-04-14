import { useEffect, useState } from 'react'
import { fetchSyllabi } from './api/client'
import ChatWindow from './components/ChatWindow'
import SyllabusList from './components/SyllabusList'
import UploadPanel from './components/UploadPanel'

export default function App() {
  const [syllabi, setSyllabi] = useState([])
  const [selectedIds, setSelectedIds] = useState([])
  const [loadError, setLoadError] = useState(null)
  const [dark, setDark] = useState(true)

  useEffect(() => {
    fetchSyllabi()
      .then(setSyllabi)
      .catch(err => setLoadError(err.message))
  }, [])

  function toggleSelected(id) {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  function handleUploaded(result) {
    fetchSyllabi()
      .then(list => {
        setSyllabi(list)
        setSelectedIds(prev =>
          prev.includes(result.syllabus_id) ? prev : [...prev, result.syllabus_id]
        )
      })
      .catch(() => {})
  }

  function handleDeleted(id) {
    setSyllabi(prev => prev.filter(s => s.id !== id))
    setSelectedIds(prev => prev.filter(x => x !== id))
  }

  const chatLabel =
    selectedIds.length === 0
      ? 'Chat — all syllabi'
      : selectedIds.length === 1
      ? `Chat — ${syllabi.find(s => s.id === selectedIds[0])?.course_code ?? 'Selected syllabus'}`
      : `Chat — ${selectedIds.length} syllabi`

  return (
    <div className={dark ? 'dark' : ''}>
      {/* Full-screen shell */}
      <div className="flex h-screen bg-gray-100 dark:bg-gray-900 font-sans transition-colors">

        {/* ── Sidebar ─────────────────────────────────────────────── */}
        <aside className="w-64 flex-shrink-0 flex flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">

          {/* Fixed: branding */}
          <div className="flex-shrink-0 px-4 py-4 border-b border-gray-100 dark:border-gray-700">
            <h1 className="text-base font-semibold text-gray-900 dark:text-gray-100">
              Syllabus Chatbot
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">ASU Course Assistant</p>
          </div>

          {/* Fixed: upload panel */}
          <div className="flex-shrink-0 pt-3">
            <p className="px-4 mb-2 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
              Upload
            </p>
            <UploadPanel onUploaded={handleUploaded} dark={dark} />
          </div>

          {/* Scrollable: syllabus list */}
          <div className="flex-1 overflow-y-auto min-h-0 pt-1">
            <div className="px-4 mb-2 flex items-center justify-between">
              <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
                Syllabi
              </p>
              {selectedIds.length > 0 && (
                <button
                  onClick={() => setSelectedIds([])}
                  className="text-xs text-amber-500 hover:text-amber-400"
                >
                  Clear
                </button>
              )}
            </div>
            {loadError ? (
              <p className="px-4 text-xs text-red-500">{loadError}</p>
            ) : (
              <SyllabusList
                syllabi={syllabi}
                selectedIds={selectedIds}
                onToggle={toggleSelected}
                onDeleted={handleDeleted}
                dark={dark}
              />
            )}
          </div>

          {/* Fixed: footer hint */}
          <div className="flex-shrink-0 border-t border-gray-100 dark:border-gray-700">
            {selectedIds.length === 0 && syllabi.length > 0 && (
              <p className="px-4 py-3 text-xs text-gray-400 dark:text-gray-500">
                Select a syllabus to scope your chat, or ask about all.
              </p>
            )}
            {selectedIds.length > 0 && (
              <p className="px-4 py-3 text-xs text-amber-500">
                {selectedIds.length === 1 ? '1 syllabus selected' : `${selectedIds.length} syllabi selected`}
              </p>
            )}
          </div>
        </aside>

        {/* ── Main chat area ───────────────────────────────────────── */}
        <main className="flex-1 flex flex-col min-w-0">

          {/* Fixed: top header */}
          <header className="flex-shrink-0 flex items-center justify-between bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-3">
            <h2 className="text-sm font-medium text-gray-700 dark:text-gray-200">
              {chatLabel}
            </h2>
            {/* Dark / light toggle */}
            <button
              onClick={() => setDark(d => !d)}
              title={dark ? 'Switch to light mode' : 'Switch to dark mode'}
              className="w-8 h-8 flex items-center justify-center rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              {dark ? (
                /* Sun icon */
                <svg className="w-4.5 h-4.5 w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
                </svg>
              ) : (
                /* Moon icon */
                <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M21 12.79A9 9 0 1111.21 3a7 7 0 009.79 9.79z" />
                </svg>
              )}
            </button>
          </header>

          {/* ChatWindow fills remaining space */}
          <ChatWindow selectedIds={selectedIds} dark={dark} />
        </main>

      </div>
    </div>
  )
}
