const BASE = ''  // Vite proxy forwards /upload, /chat, /syllabi → http://localhost:8001

/** Fetch all syllabi ordered by most-recent first. */
export async function fetchSyllabi() {
  const res = await fetch(`${BASE}/syllabi`)
  if (!res.ok) throw new Error(`GET /syllabi failed: ${res.status}`)
  return res.json()
}

/** Upload a PDF or DOCX file. Returns the SyllabusUploadResponse JSON. */
export async function uploadSyllabus(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Upload failed')
  }
  return res.json()
}

/** Delete a syllabus by id. */
export async function deleteSyllabus(id) {
  const res = await fetch(`${BASE}/syllabi/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Delete failed')
  }
}

/**
 * Stream a chat response from the backend.
 *
 * Calls onToken(string) for each streamed text chunk.
 * Calls onDone() when the stream closes.
 * Calls onError(Error) on network or HTTP errors.
 *
 * @param {string} message
 * @param {number[]} syllabusIds  — empty array = search all
 * @param {{ onToken, onDone, onError }} callbacks
 * @returns {AbortController}  — call .abort() to cancel mid-stream
 */
export function streamChat(message, syllabusIds, { onToken, onDone, onError }) {
  const controller = new AbortController()

  ;(async () => {
    let res
    try {
      res = await fetch(`${BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, syllabus_ids: syllabusIds }),
        signal: controller.signal,
      })
    } catch (err) {
      if (err.name !== 'AbortError') onError(err)
      return
    }

    if (!res.ok) {
      const detail = await res.json().catch(() => ({ detail: res.statusText }))
      onError(new Error(detail.detail ?? 'Chat request failed'))
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        onToken(decoder.decode(value, { stream: true }))
      }
      onDone()
    } catch (err) {
      if (err.name !== 'AbortError') onError(err)
    }
  })()

  return controller
}
