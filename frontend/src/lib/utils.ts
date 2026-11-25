import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNowStrict, parseISO } from 'date-fns'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatDate(iso: string, pattern = 'd MMM yyyy'): string {
  try {
    return format(parseISO(iso), pattern)
  } catch {
    return '-'
  }
}

/** Format a stored timestamp for people while keeping the source value intact. */
export function formatDateTime(value: unknown): string {
  if (value == null || value === '') return '—'
  const text = String(value)
  const date = value instanceof Date
    ? value
    : /^\d{4}-\d{2}-\d{2}$/.test(text)
      ? new Date(`${text}T00:00:00`)
      : new Date(text)
  if (Number.isNaN(date.getTime())) return String(value)
  const hasTime = /T\d{2}:\d{2}/.test(text)
  return new Intl.DateTimeFormat(undefined, hasTime
    ? { dateStyle: 'medium', timeStyle: 'short' }
    : { dateStyle: 'medium' }).format(date)
}

/** Keep identifiers scannable in tables; the full value remains available in title text. */
export function formatIdentifier(value: unknown): string {
  if (value == null || value === '') return '—'
  const id = String(value)
  if (/^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i.test(id)) {
    return `${id.slice(0, 8)}…${id.slice(-4)}`
  }
  return id.length > 28 ? `${id.slice(0, 12)}…${id.slice(-6)}` : id
}

/** Convert API field names and machine values into readable labels and dates. */
export function formatFieldLabel(value: string): string {
  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
    .replace(/\bId\b/g, 'ID')
    .replace(/\bUrl\b/g, 'URL')
}

export function formatFieldValue(field: string, value: unknown): string {
  if (value == null || value === '') return '—'
  if (/(?:^|_)(?:id|uuid)$/.test(field) || /(?:^|_)(?:user|project|request|run|owner)_id$/.test(field)) {
    return formatIdentifier(value)
  }
  if (/(?:^|_)(?:at|on|date|time)$/.test(field)) return formatDateTime(value)
  if (/(?:^|_)(?:status|event|role|kind|type|decision)$/.test(field)) {
    return formatFieldLabel(String(value))
  }
  if (typeof value === 'string' && /^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i.test(value)) {
    return formatIdentifier(value)
  }
  return String(value)
}

export function formatRelative(iso: string): string {
  try {
    return `${formatDistanceToNowStrict(parseISO(iso))} ago`
  } catch {
    return '-'
  }
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const seconds = ms / 1000
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  const rest = Math.round(seconds % 60)
  return `${minutes}m ${rest}s`
}

export function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(
    value,
  )
}

export function formatUsd(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: value < 1 ? 3 : 2,
    maximumFractionDigits: value < 1 ? 3 : 2,
  }).format(value)
}

export function formatPercent(value01: number): string {
  return `${Math.round(value01 * 100)}%`
}

/** "Acme Digital" -> "AD". Used by avatars and project tiles. */
export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? '')
    .join('')
}

/** Strips protocol and trailing slash for display: "https://a.com/" -> "a.com". */
export function prettyUrl(url: string): string {
  return url.replace(/^https?:\/\//, '').replace(/\/$/, '')
}

export function truncate(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max - 1).trimEnd()}…`
}

export function titleCase(value: string): string {
  return value
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Small deterministic id for mock data and optimistic rows. */
export function makeId(prefix = 'id'): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}
