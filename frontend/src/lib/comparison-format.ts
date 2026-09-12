import type { MetricRow } from '@/types/domain'
import { titleCase } from './utils'

const NUMBER = new Intl.NumberFormat('en-PK', { maximumFractionDigits: 2 })
const CENTS = new Intl.NumberFormat('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
/** Unit prices under one currency unit keep their sub-cent digits (US$0.0035). */
const SMALL_AMOUNT = new Intl.NumberFormat('en-PK', { minimumFractionDigits: 2, maximumFractionDigits: 4 })

/**
 * An amount in its listing's currency.
 *
 * Daraz prices are rupees ("Rs. 626"), formatted as they always have been. No
 * currency at all means rupees, which is what Daraz rows have always been.
 * Alibaba's are US dollars with cents ("US$9.50", "US$0.0035"); any other ISO
 * code is written in front of the amount.
 */
export function formatMoney(value: number, currency: string | null = 'PKR'): string {
  const code = (currency ?? '').trim().toUpperCase()
  if (code === '' || code === 'PKR') return `Rs. ${NUMBER.format(value)}`

  const format = Number.isInteger(value) ? NUMBER : Math.abs(value) < 1 ? SMALL_AMOUNT : CENTS
  const amount = format.format(value)
  return code === 'USD' ? `US$${amount}` : `${code} ${amount}`
}

/**
 * The unit for one side of a metric row.
 *
 * When the two listings disagree -- priced in two currencies, or ordered in
 * pieces vs boxes -- the backend sends "USD vs EUR", your listing first, and
 * marks the row not comparable.
 */
function unitFor(unit: string | null, side: 'own' | 'competitor' | undefined): string | null {
  if (!unit || !side || !unit.includes(' vs ')) return unit
  const [own, competitor] = unit.split(' vs ')
  return (side === 'own' ? own : competitor) ?? null
}

/**
 * A unit word for a quantity of one: "pieces" -> "piece", "boxes" -> "box",
 * "days" -> "day". Mirrors unit_key in app/scrapers/alibaba/extract.py. One
 * unit label serves both sides of a row, and it is sent in the plural.
 */
function singularUnit(unit: string): string {
  if (/[^aeiou]ies$/i.test(unit) && unit.length > 4) return `${unit.slice(0, -3)}y`
  if (/(x|s|ch|sh)es$/i.test(unit)) return unit.slice(0, -2)
  if (/[^s]s$/i.test(unit) && unit.length > 2) return unit.slice(0, -1)
  return unit
}

/** One metric cell, formatted by the kind the backend declares for it. */
export function formatMetric(
  value: MetricRow['own'],
  kind: MetricRow['kind'],
  unit: string | null,
  side?: 'own' | 'competitor',
): string {
  if (value === null || value === undefined || value === '') return '—'
  const sideUnit = unitFor(unit, side)

  switch (kind) {
    case 'currency':
      return typeof value === 'number' ? formatMoney(value, sideUnit) : String(value)
    case 'percent':
      return typeof value === 'number'
        ? `${NUMBER.format(value)}${unit === '/100' ? ' / 100' : '%'}`
        : String(value)
    case 'rating':
      return typeof value === 'number' ? `${value.toFixed(1)} / 5` : String(value)
    case 'bool':
      return value ? 'Yes' : 'No'
    case 'number': {
      if (typeof value !== 'number') return String(value)
      const word = sideUnit && value === 1 ? singularUnit(sideUnit) : sideUnit
      return `${NUMBER.format(value)}${word ? ` ${word}` : ''}`
    }
    default:
      return String(value)
  }
}

/** A listing's price, as a range when its unit price varies (quantity tiers). */
export function formatPrice(
  value: number | null,
  currency: string | null = 'PKR',
  maxValue: number | null = null,
): string {
  if (value === null) return '—'
  const lowest = formatMoney(value, currency)
  return maxValue !== null && maxValue > value ? `${lowest} – ${formatMoney(maxValue, currency)}` : lowest
}

/** "100 pieces". */
export function formatQuantity(quantity: number, unit: string | null): string {
  return `${NUMBER.format(quantity)}${unit ? ` ${unit}` : ''}`
}

const FIELD_LABELS: Record<string, string> = {
  title: 'Title',
  description: 'Description',
  specs: 'Specifications',
  review: 'Customer reviews',
  promo_tags: 'Promotional tags',
  policy_text: 'Policy & warranty',
  category: 'Category path',
  order_terms: 'Order terms & price tiers',
  supplier: 'Supplier profile',
}

/** A scraped text field's display name. */
export function formatFieldType(fieldType: string): string {
  return FIELD_LABELS[fieldType] ?? titleCase(fieldType)
}

/** "credibility_index" -> "credibility index"; booleans read as yes/no. */
export function formatDerived(key: string, value: unknown): { label: string; value: string } {
  return {
    label: key.replace(/_/g, ' '),
    value:
      value === null || value === undefined
        ? '—'
        : typeof value === 'boolean'
          ? value
            ? 'yes'
            : 'no'
          : String(value),
  }
}
