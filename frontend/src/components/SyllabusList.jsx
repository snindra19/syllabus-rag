import { deleteSyllabus } from '../api/client'

export default function SyllabusList({ syllabi, selectedIds, onToggle, onDeleted }) {
  async function handleDelete(e, id) {
    e.stopPropagation()
    if (!confirm('Delete this syllabus and all its data?')) return
    try {
      await deleteSyllabus(id)
      onDeleted(id)
    } catch (err) {
      alert(`Delete failed: ${err.message}`)
    }
  }

  if (syllabi.length === 0) {
    return (
      <p className="px-4 py-3 text-xs text-gray-400 dark:text-gray-500">
        No syllabi uploaded yet.
      </p>
    )
  }

  return (
    <ul className="space-y-1 px-2 pb-2">
      {syllabi.map(s => {
        const selected = selectedIds.includes(s.id)
        const label = s.course_code ?? s.filename
        const sub = s.course_title ?? s.filename

        return (
          <li key={s.id}>
            <button
              onClick={() => onToggle(s.id)}
              className={`
                w-full text-left rounded-lg px-3 py-2 flex items-start justify-between gap-2 group
                transition-colors text-sm
                ${selected
                  ? 'bg-amber-50 dark:bg-amber-900/30 border border-amber-300 dark:border-amber-700'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-700/50 border border-transparent'}
              `}
            >
              <div className="min-w-0">
                <p className={`font-medium truncate ${selected
                  ? 'text-amber-700 dark:text-amber-400'
                  : 'text-gray-800 dark:text-gray-200'}`}>
                  {label}
                </p>
                {sub !== label && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">{sub}</p>
                )}
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                  {new Date(s.upload_date).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={e => handleDelete(e, s.id)}
                title="Delete syllabus"
                className="flex-shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 transition-opacity"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </button>
          </li>
        )
      })}
    </ul>
  )
}
