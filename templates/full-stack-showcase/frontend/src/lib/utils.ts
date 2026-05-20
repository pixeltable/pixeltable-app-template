import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function toDataUrl(b64: string | undefined, format = 'png'): string {
  if (!b64) return ''
  if (b64.startsWith('data:')) return b64
  return `data:image/${format};base64,${b64}`
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return '--'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function formatTimestamp(iso: string | null | undefined): string {
  if (!iso) return '--'
  return new Date(iso).toLocaleString()
}
