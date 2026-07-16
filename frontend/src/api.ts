import type { Analysis, HistoryItem, Stats } from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init)
  if (!response.ok) throw new Error('Sentinel service is unavailable. Check that the API is running.')
  return response.json() as Promise<T>
}
export const analyze = (prompt: string) => request<Analysis>('/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt }) })
export const getHistory = () => request<HistoryItem[]>('/history')
export const getStats = () => request<Stats>('/stats')
