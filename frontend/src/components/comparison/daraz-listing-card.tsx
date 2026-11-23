import { useState } from 'react'
import { ArrowUpRight, Check, ChevronLeft, ChevronRight } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { SafeImage } from '@/components/shared/safe-image'
import type { EcommerceProduct, ProductImage } from '@/types/domain'

function count(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function rs(value: number | null): string {
  return value === null ? '—' : `Rs ${Math.round(value).toLocaleString()}`
}

/**
 * One Daraz listing as it was read, in the same style as an Instagram profile card: who it is, the price, how many
 * sold and the rating, its photos, and the offers Daraz shows on the search page. Nothing is scored here: what to
 * change comes from Find gaps, which compares both listings with the top Daraz listings.
 */
export function DarazListingCard({ product }: { product: EcommerceProduct }) {
  const isOwn = product.role === 'own'
  const meta = product.rawMetadata ?? {}
  const sold = count(meta.sold)
  const options = count(meta.variant_count)
  // The sale price is read from Daraz search; when that fails, only the price before discount is known.
  const beforeDiscount = String(meta.price_source ?? '').startsWith('price before discount')
  const offers = [
    meta.free_shipping ? 'Free shipping' : null,
    meta.voucher ? 'Voucher' : null,
    meta.coins ? 'Coins discount' : null,
    meta.daraz_choice ? 'Daraz Choice' : null,
  ].filter(Boolean) as string[]

  return (
    <Card className="relative flex h-full flex-col overflow-hidden p-0">
      <div
        className={
          isOwn
            ? 'h-1.5 bg-gradient-to-r from-primary to-primary/40'
            : 'h-1.5 bg-gradient-to-r from-warning to-warning/40'
        }
      />
      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <p
              className={
                isOwn ? 'text-xs font-semibold text-primary' : 'text-xs font-semibold text-warning-ink'
              }
            >
              {isOwn ? 'Your listing' : 'Competitor'}
            </p>
            <h3
              className="mt-0.5 line-clamp-2 font-display text-base font-bold"
              title={product.productName}
            >
              {product.productName}
            </h3>
          </div>
          <a
            href={product.url}
            target="_blank"
            rel="noreferrer"
            className="flex size-9 shrink-0 items-center justify-center rounded-full border border-border/30 text-muted-foreground transition hover:border-primary/40 hover:text-primary"
            aria-label="Open on Daraz"
            title="Open on Daraz"
          >
            <ArrowUpRight className="size-4" />
          </a>
        </div>

        <div className="mt-4 flex items-end justify-between gap-3 rounded-2xl bg-muted/40 px-4 py-3">
          <div>
            <p className="text-xs text-muted-foreground">
              {beforeDiscount ? 'Price before discount' : 'Price'}
            </p>
            <p className="font-display text-2xl font-extrabold tabular-nums">{rs(product.price)}</p>
            {beforeDiscount ? (
              <p className="text-xs text-warning-ink">Sale price not read this time. Scrape again.</p>
            ) : product.originalPrice && product.price && product.originalPrice > product.price ? (
              <p className="text-xs text-muted-foreground">
                <span className="line-through">{rs(product.originalPrice)}</span>
                {product.discountPercent ? ` · ${Math.round(product.discountPercent)}% off` : ''}
              </p>
            ) : null}
          </div>
          <div className="flex gap-4 text-right">
            <Mini
              label="Sold"
              value={sold === null ? '—' : sold.toLocaleString()}
              hint={sold === null ? 'Daraz shows this only on its search page, and it could not be read this time.' : undefined}
            />
            <Mini
              label="Rating"
              value={product.rating !== null ? `${product.rating.toFixed(1)} ★` : '—'}
            />
            <Mini label="Reviews" value={product.reviewCount.toLocaleString()} />
          </div>
        </div>

        <PhotoStrip images={product.images} name={product.productName} />

        <ul className="mt-4 flex flex-wrap gap-1.5 text-xs">
          <Chip>
            {product.imageCount} photo{product.imageCount === 1 ? '' : 's'}
          </Chip>
          {options !== null ? (
            <Chip>
              {options} colour / size option{options === 1 ? '' : 's'}
            </Chip>
          ) : null}
          {offers.map((o) => (
            <Chip key={o} good>
              {o}
            </Chip>
          ))}
        </ul>
      </div>
    </Card>
  )
}

function Mini({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div title={hint}>
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="text-sm font-bold tabular-nums">{value}</p>
    </div>
  )
}

function Chip({ children, good = false }: { children: React.ReactNode; good?: boolean }) {
  return (
    <li
      className={
        good
          ? 'inline-flex items-center gap-1 rounded-full bg-success/10 px-2.5 py-1 font-medium text-success'
          : 'rounded-full bg-muted/50 px-2.5 py-1 text-muted-foreground'
      }
    >
      {good ? <Check className="size-3" aria-hidden="true" /> : null}
      {children}
    </li>
  )
}

const arrow =
  'flex size-8 items-center justify-center rounded-full border border-border/30 bg-card text-primary shadow-sm transition hover:bg-primary hover:text-primary-foreground disabled:pointer-events-none disabled:opacity-30'

/** The listing's photos, three at a time (like the posts on an Instagram card); each one opens full size. */
function PhotoStrip({ images, name }: { images: ProductImage[]; name: string }) {
  const PAGE = 3
  const [start, setStart] = useState(0)
  const [open, setOpen] = useState<number | null>(null)
  if (images.length === 0) {
    return <p className="mt-4 text-sm text-muted-foreground">No photos could be read for this listing.</p>
  }
  const last = Math.max(0, images.length - PAGE)
  const shown = images.slice(start, start + PAGE)
  const current = open === null ? null : images[open]
  return (
    <div className="mt-4">
      <ul className="grid grid-cols-3 gap-2">
        {shown.map((image, i) => (
          <li key={image.id}>
            <button
              type="button"
              onClick={() => {
                setOpen(start + i)
              }}
              className="block w-full overflow-hidden rounded-md border border-border/15 transition-colors hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={`Open photo ${start + i + 1} of ${images.length}`}
            >
              <SafeImage src={image.url} alt="" className="aspect-square w-full border-0" fit="cover" compact />
            </button>
          </li>
        ))}
      </ul>
      {images.length > PAGE ? (
        <div className="mt-2 flex items-center justify-between">
          <button
            type="button"
            className={arrow}
            disabled={start === 0}
            onClick={() => {
              setStart((v) => Math.max(0, v - PAGE))
            }}
            aria-label="Previous photos"
          >
            <ChevronLeft className="size-4" />
          </button>
          <span className="text-xs text-muted-foreground">
            {start + 1}–{Math.min(start + PAGE, images.length)} of {images.length} photos
          </span>
          <button
            type="button"
            className={arrow}
            disabled={start >= last}
            onClick={() => {
              setStart((v) => Math.min(last, v + PAGE))
            }}
            aria-label="Next photos"
          >
            <ChevronRight className="size-4" />
          </button>
        </div>
      ) : null}

      <Dialog
        open={current !== null}
        onOpenChange={(value) => {
          if (!value) setOpen(null)
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogTitle className="line-clamp-1 pr-8 text-base">{name}</DialogTitle>
          {current && open !== null ? (
            <div className="space-y-3">
              <SafeImage src={current.url} alt={`${name}, photo ${open + 1}`} className="max-h-[65vh] w-full border-0" fit="contain" />
              <div className="flex items-center justify-between">
                <button
                  type="button"
                  className={arrow}
                  disabled={open === 0}
                  onClick={() => {
                    setOpen(open - 1)
                  }}
                  aria-label="Previous photo"
                >
                  <ChevronLeft className="size-4" />
                </button>
                <span className="text-sm text-muted-foreground">
                  Photo {open + 1} of {images.length}
                </span>
                <button
                  type="button"
                  className={arrow}
                  disabled={open >= images.length - 1}
                  onClick={() => {
                    setOpen(open + 1)
                  }}
                  aria-label="Next photo"
                >
                  <ChevronRight className="size-4" />
                </button>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
