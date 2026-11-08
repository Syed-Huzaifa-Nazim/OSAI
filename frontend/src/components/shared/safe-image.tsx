import { useState } from 'react'
import { ImageOff } from 'lucide-react'
import { cn } from '@/lib/utils'

/**
 * A remote image that fails on its own.
 *
 * Every scraper stores the source's own URL rather than re-hosting the file, so
 * each image is a live request to a marketplace, a site or Instagram's CDN, and
 * any one of them can 404, expire or be blocked. This renders a placeholder in
 * that case, so one broken link never takes a card's layout with it.
 *
 * Shared by the product gallery, the scraped-page cards and the Instagram post
 * grid: one behaviour for every image the product shows.
 */

interface SafeImageProps {
  src: string
  alt: string
  className?: string
  loading?: 'lazy' | 'eager'
  /** Icon-only placeholder, for thumbnails too small for text. */
  compact?: boolean
  /** `contain` keeps a product photo whole; `cover` fills a grid tile. */
  fit?: 'contain' | 'cover'
}

export function SafeImage({
  src,
  alt,
  className,
  loading = 'lazy',
  compact = false,
  fit = 'contain',
}: SafeImageProps) {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <ImagePlaceholder className={className} label={compact ? undefined : 'Image unavailable'} />
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      loading={loading}
      decoding="async"
      referrerPolicy="no-referrer"
      onError={() => {
        setFailed(true)
      }}
      className={cn(
        'rounded-md border border-border/15 bg-muted/25',
        fit === 'cover' ? 'object-cover' : 'object-contain',
        className,
      )}
    />
  )
}

export function ImagePlaceholder({ className, label }: { className?: string; label?: string }) {
  return (
    <div
      role="img"
      aria-label={label ?? 'Image unavailable'}
      className={cn(
        'flex flex-col items-center justify-center gap-1.5 rounded-md border border-dashed border-border/25 bg-muted/25 text-muted-foreground',
        className,
      )}
    >
      <ImageOff className="size-4" aria-hidden="true" />
      {label ? <span className="px-3 text-center text-xs">{label}</span> : null}
    </div>
  )
}
