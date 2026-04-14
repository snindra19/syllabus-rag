import { useRef, useState } from 'react'
import { uploadSyllabus } from '../api/client'

export default function UploadPanel({ onUploaded }) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  async function handleFile(file) {
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['pdf', 'docx', 'doc'].includes(ext)) {
      setError('Only PDF and DOCX files are supported.')
      return
    }
    setError(null)
    setUploading(true)
    try {
      const result = await uploadSyllabus(file)
      onUploaded(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  return (
    <div className="px-3 pb-3">
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !uploading && inputRef.current?.click()}
        className={`
          relative flex flex-col items-center justify-center gap-1.5
          border-2 border-dashed rounded-xl px-3 py-5 text-center
          cursor-pointer transition-colors select-none
          ${dragging
            ? 'border-amber-400 bg-amber-50 dark:bg-amber-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20'}
          ${uploading ? 'opacity-60 cursor-wait' : ''}
        `}
      >
        {uploading ? (
          <>
            <svg className="w-6 h-6 text-amber-500 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor"
                d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z" />
            </svg>
            <p className="text-xs text-gray-500 dark:text-gray-400">Processing syllabus…</p>
          </>
        ) : (
          <>
            <svg className="w-6 h-6 text-gray-400 dark:text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            <p className="text-xs text-gray-600 dark:text-gray-300 font-medium">Drop PDF or DOCX here</p>
            <p className="text-xs text-gray-400 dark:text-gray-500">or click to browse</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.doc"
          className="hidden"
          onChange={e => handleFile(e.target.files[0])}
        />
      </div>
      {error && (
        <p className="mt-1.5 text-xs text-red-500 px-1">{error}</p>
      )}
    </div>
  )
}
