const apiRoot = import.meta.env.VITE_API_URL ?? ''

export type Video = { video_id: string; url: string; title: string; thumbnail_url: string; duration_seconds: number; transcript_language: string; transcript_source: string }
export type ProcessResult = { video: Video; summary: string; indexed_chunks: number; already_indexed: boolean }
export type Source = { start_seconds: number; end_seconds: number; label: string; excerpt: string }
export type ChatResult = { answer: string; sources: Source[] }

async function request<T>(path: string, body: object): Promise<T> {
  const response = await fetch(`${apiRoot}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Something went wrong. Please try again.')
  return data as T
}
export const processVideo = (url: string) => request<ProcessResult>('/api/videos/process', { url })
export const askVideo = (video_id: string, question: string) => request<ChatResult>('/api/chat', { video_id, question })
