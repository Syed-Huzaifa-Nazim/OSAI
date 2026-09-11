import type { MetricRow } from '@/types/domain'
import { titleCase } from './utils'

const NUMBER = new Intl.NumberFormat('en-PK', { maximumFractionDigits: 2 })

/** One metric cell, formatted by the kind the backend declares for it. */
export function formatMetric(
  value: MetricRow['own'],
  kind: MetricRow['kind'],
  unit: string | null,
): string {
  if (value === null || value === undefined || value === '') return '—'

  switch (kind) {
    case 'currency':
      return typeof value === 'number' ? `Rs. ${NUMBER.format(value)}` : String(value)
    case 'percent':
      return typeof value === 'number'
        ? `${NUMBER.format(value)}${unit === '/100' ? ' / 100' : '%'}`
        : String(value)
    case 'rating':
      return typeof value === 'number' ? `${value.toFixed(1)} / 5` : String(value)
    case 'bool':
      return value ? 'Yes' : 'No'
    case 'number':
      return typeof value === 'number'
        ? `${NUMBER.format(value)}${unit ? ` ${unit}` : ''}`
        : String(value)
    default:
      return String(value)
  }
}

export function formatPrice(value: number | null): string {
  return value === null ? '—' : `Rs. ${NUMBER.format(value)}`
}

const FIELD_LABELS: Record<string, string> = {
  title: 'Title',
  description: 'Description',
  specs: 'Specifications',
  review: 'Customer reviews',
  promo_tags: 'Promotional tags',
  policy_text: 'Policy & warranty',
  category: 'Category path',
}

/** A scraped text field's display name. */
export function formatFieldType(fieldType: string): string {
  return FIELD_LABELS[fieldType] ?? titleCase(fieldType)
}

/** "credibility_index" -> "credibility index"; booleans read as yes/no. */
export function formatDerived(key: string, value: unknown): { label: string; value: string } {
  return {
    label: key.replace(/_/g, ' '),
    value: typeof value === 'boolean' ? (value ? 'yes' : 'no') : String(value),
  }
}
