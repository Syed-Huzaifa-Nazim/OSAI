import { useState } from 'react'
import { ImagePlaceholder, SafeImage } from '@/components/shared/safe-image'
import { cn } from '@/lib/utils'
import type { ProductImage } from '@/types/domain'

/** Thumbnails shown under the main image before the rest collapse into "+N". */
const VISIBLE_THUMBNAILS = 6

interface ProductGalleryProps {
  images: ProductImage[]
  productName: string
}

/**
 * A listing's main image with its gallery as selectable thumbnails.
 *
 * Images load straight from the marketplace's CDN. They are lazy, sent without
 * a referrer, and each one degrades to a placeholder on its own if it fails, so
 * one broken link never takes the card's layout with it.
 */
export function ProductGallery({ images, productName }: ProductGalleryProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = images.find((image) => image.id === selectedId) ?? images[0]

  if (!selected) {
    return (
      <ImagePlaceholder
        className="aspect-[4/3] w-full"
        label="No product images were found on this listing"
      />
    )
  }

  const hidden = Math.max(0, images.length - VISIBLE_THUMBNAILS)

  return (
    <div className="space-y-2">
      <SafeImage
        key={selected.id}
        src={selected.url}
        alt={`${productName}, image ${selected.position}`}
        className="aspect-[4/3] w-full"
        loading="eager"
      />

      {images.length > 1 ? (
        <div className="flex flex-wrap items-center gap-1.5">
          {images.slice(0, VISIBLE_THUMBNAILS).map((image) => {
            const isSelected = image.id === selected.id
            return (
              <button
                key={image.id}
                type="button"
                onClick={() => {
                  setSelectedId(image.id)
                }}
                aria-label={`Show image ${image.position} of ${images.length}`}
                aria-pressed={isSelected}
                className={cn(
                  'overflow-hidden rounded-md border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  isSelected ? 'border-primary/60' : 'border-border/20 hover:border-primary/35',
                )}
              >
                <SafeImage src={image.url} alt="" className="size-11 border-0" compact />
              </button>
            )
          })}
          {hidden > 0 ? (
            <span className="px-1 text-xs text-muted-foreground">+{hidden} more</span>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

interface ImageStripProps {
  images: ProductImage[]
  productName: string
}

/** Every photo of a listing at a glance, for side-by-side content comparisons. */
export function ImageStrip({ images, productName }: ImageStripProps) {
  if (images.length === 0) {
    return <p className="text-sm text-muted-foreground">No product images were found on this listing.</p>
  }

  return (
    <ul className="grid grid-cols-4 gap-2 sm:grid-cols-5">
      {images.map((image) => (
        <li key={image.id}>
          <a
            href={image.url}
            target="_blank"
            rel="noreferrer"
            className="block rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={`Open image ${image.position} of ${productName}`}
          >
            <SafeImage
              src={image.url}
              alt={`${productName}, image ${image.position}`}
              className="aspect-square w-full"
              compact
            />
          </a>
        </li>
      ))}
    </ul>
  )
}

