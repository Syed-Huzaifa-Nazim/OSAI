import { describe, expect, it } from 'vitest'
import {
  formatDerived,
  formatFieldType,
  formatMetric,
  formatMoney,
  formatPrice,
  formatQuantity,
} from '@/lib/comparison-format'

describe('formatMoney', () => {
  it('writes rupees the way Daraz rows always have', () => {
    expect(formatMoney(626, 'PKR')).toBe('Rs. 626')
    expect(formatMoney(1799.5)).toBe('Rs. 1,799.5')
    expect(formatMoney(626, null)).toBe('Rs. 626')
  })

  it('writes US dollars for Alibaba, with cents and sub-cent unit prices', () => {
    expect(formatMoney(12.99, 'USD')).toBe('US$12.99')
    expect(formatMoney(9.5, 'USD')).toBe('US$9.50')
    expect(formatMoney(0.75, 'usd')).toBe('US$0.75')
    expect(formatMoney(0.5, 'USD')).toBe('US$0.50')
    expect(formatMoney(0.0035, 'USD')).toBe('US$0.0035')
    expect(formatMoney(1200, 'USD')).toBe('US$1,200')
  })

  it('names any other currency', () => {
    expect(formatMoney(3.5, 'EUR')).toBe('EUR 3.50')
  })
})

describe('formatPrice', () => {
  it('shows a range only when the unit price varies', () => {
    expect(formatPrice(0.75, 'USD', 0.77)).toBe('US$0.75 – US$0.77')
    expect(formatPrice(1.85, 'USD', 1.85)).toBe('US$1.85')
    expect(formatPrice(626, 'PKR', null)).toBe('Rs. 626')
    expect(formatPrice(null, 'USD', 2)).toBe('—')
  })
})

describe('formatMetric', () => {
  it('uses the currency the row declares', () => {
    expect(formatMetric(626, 'currency', 'PKR')).toBe('Rs. 626')
    expect(formatMetric(0.75, 'currency', 'USD', 'own')).toBe('US$0.75')
  })

  it("gives each side its own unit when the listings disagree", () => {
    expect(formatMetric(0.75, 'currency', 'USD vs EUR', 'own')).toBe('US$0.75')
    expect(formatMetric(3.1, 'currency', 'USD vs EUR', 'competitor')).toBe('EUR 3.10')
    expect(formatMetric(100, 'number', 'pieces vs boxes', 'own')).toBe('100 pieces')
    expect(formatMetric(20, 'number', 'pieces vs boxes', 'competitor')).toBe('20 boxes')
  })

  it('writes the singular unit for a quantity of one', () => {
    expect(formatMetric(1, 'number', 'pieces', 'competitor')).toBe('1 piece')
    expect(formatMetric(100, 'number', 'pieces', 'own')).toBe('100 pieces')
    expect(formatMetric(1, 'number', 'boxes')).toBe('1 box')
    expect(formatMetric(1, 'number', 'batteries')).toBe('1 battery')
    expect(formatMetric(1, 'number', 'days')).toBe('1 day')
    expect(formatMetric(1, 'number', 'glass')).toBe('1 glass')
    expect(formatMetric(1, 'number', '-1..+1')).toBe('1 -1..+1')
  })

  it('keeps the existing kinds unchanged', () => {
    expect(formatMetric(1000, 'number', 'pieces')).toBe('1,000 pieces')
    expect(formatMetric(98.2, 'percent', '%')).toBe('98.2%')
    expect(formatMetric(66.7, 'percent', '/100')).toBe('66.7 / 100')
    expect(formatMetric(4.9, 'rating', '/5')).toBe('4.9 / 5')
    expect(formatMetric(true, 'bool', null)).toBe('Yes')
    expect(formatMetric(null, 'number', 'days')).toBe('—')
    expect(formatMetric('5-day dispatch', 'text', null)).toBe('5-day dispatch')
  })
})

describe('labels', () => {
  it("names Alibaba's text fields", () => {
    expect(formatFieldType('order_terms')).toBe('Order terms & price tiers')
    expect(formatFieldType('supplier')).toBe('Supplier profile')
    expect(formatFieldType('review')).toBe('Customer reviews')
  })

  it('formats quantities and derived figures', () => {
    expect(formatQuantity(100, 'pieces')).toBe('100 pieces')
    expect(formatQuantity(3000, null)).toBe('3,000')
    expect(formatDerived('entry_order_value', null)).toEqual({ label: 'entry order value', value: '—' })
    expect(formatDerived('orderable_now', true)).toEqual({ label: 'orderable now', value: 'yes' })
    expect(formatDerived('trust_badges', 2)).toEqual({ label: 'trust badges', value: '2' })
  })
})
