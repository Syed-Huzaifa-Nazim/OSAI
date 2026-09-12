import { ArrowUpRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { formatPrice, formatQuantity } from '@/lib/comparison-format'
import type { EcommerceProduct } from '@/types/domain'
import { ProductGallery } from './product-gallery'

interface ProductSummaryCardProps {
  product: EcommerceProduct
  platformLabel: string
}

/** One scraped listing at a glance: its photos, the headline figures, and how
 *  it was read. */
export function ProductSummaryCard({ product, platformLabel }: ProductSummaryCardProps) {
  const isOwn = product.role === 'own'

  return (
    <Card className="flex h-full flex-col p-5">
      <div className="flex items-center justify-between gap-3">
        <Badge variant={isOwn ? 'default' : 'secondary'}>
          {isOwn ? 'Your product' : 'Competitor'}
        </Badge>
        <a
          href={product.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary"
        >
          View on {platformLabel}
          <ArrowUpRight className="size-3" />
        </a>
      </div>

      <div className="mt-3">
        <ProductGallery images={product.images} productName={product.productName} />
      </div>

      <h3
        className="mt-3 line-clamp-2 font-display text-base font-semibold"
        title={product.productName}
      >
        {product.productName}
      </h3>

      <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
        <Stat label="Price" value={formatPrice(product.price, product.currency, product.maxPrice)} />
        <Stat label="Brand" value={product.brand ?? '—'} />
        <Stat
          label="Rating"
          value={product.rating !== null ? `${product.rating.toFixed(1)} / 5` : '—'}
        />
        <Stat label="Reviews" value={product.reviewCount.toLocaleString()} />
        {/* Wholesale platforms (Alibaba) only; a Daraz card is unchanged. */}
        {product.moq !== null ? (
          <Stat label="Min. order" value={formatQuantity(product.moq, product.moqUnit)} />
        ) : null}
        {product.supplier ? <Stat label="Supplier" value={product.supplier.name} /> : null}
      </dl>

      <p className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-border/15 pt-4 text-xs text-muted-foreground">
        <span>{product.chunkCount} chunks embedded</span>
        <span aria-hidden="true">·</span>
        <span>
          {product.imageCount} image{product.imageCount === 1 ? '' : 's'}
        </span>
        <span aria-hidden="true">·</span>
        <span className="font-mono">{product.scrapeMethod}</span>
      </p>

      {product.warnings.length > 0 ? (
        <details className="mt-3 text-xs text-muted-foreground">
          <summary className="cursor-pointer select-none hover:text-foreground">
            {product.warnings.length} scrape note{product.warnings.length === 1 ? '' : 's'}
          </summary>
          <ul className="mt-2 list-disc space-y-1 pl-4">
            {product.warnings.map((warning, index) => (
              <li key={index}>{warning}</li>
            ))}
          </ul>
        </details>
      ) : null}
    </Card>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="truncate text-sm font-medium tabular-nums" title={value}>
        {value}
      </dd>
    </div>
  )
}
