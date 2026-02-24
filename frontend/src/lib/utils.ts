import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Wrap raw base64 from Pixeltable's b64_encode UDF into a data-URL for <img src>. */
export function toDataUrl(b64: string | undefined, format = 'png'): string {
  if (!b64) return ''
  if (b64.startsWith('data:')) return b64
  return `data:image/${format};base64,${b64}`
}
