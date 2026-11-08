import { AnimatePresence, motion } from 'framer-motion'
import { ArrowUpRight, Heart, MapPin } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { SafeImage } from '@/components/shared/safe-image'
import { usePrefersReducedMotion } from '@/hooks/use-reduced-motion'
import { mediaSrc } from '@/lib/media'
import { formatDate } from '@/lib/utils'
import { spring } from '@/lib/motion'
import type { ScrapedPost } from '@/types/domain'
import { useEffect, useState } from 'react'

/**
 * One scraped post, opened from the profile grid.
 *
 * Everything the scraper actually collected for that post and nothing it did
 * not: the media it carries, the caption as written, its engagement counts, its
 * hashtags, and the public comments that were read for it. A post with no
 * comments says so rather than showing an empty panel, because "none were
 * collected" and "nobody commented" are different facts.
 *
 * Built from the app's own dialog, badges and image handling, so it belongs to
 * the same surface as the rest of the product. Motion follows the shared
 * spring, and collapses to a fade when the viewer asks for reduced motion.
 */

interface PostDetailDialogProps {
  post: ScrapedPost | null
  /** The profile this post was collected from. */
  username: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function PostDetailDialog({ post, username, open, onOpenChange }: PostDetailDialogProps) {
  const [slide, setSlide] = useState(0)
  const reduced = usePrefersReducedMotion()

  // A different post starts at its first slide, not wherever the last one was.
  useEffect(() => {
    setSlide(0)
  }, [post?.id])

  const media = post?.media ?? []
  const current = media[slide] ?? media[0]
  const url = current?.mediaUrl ?? post?.mediaUrl ?? null
  const comments = post?.comments ?? []
  // A collaboration post is published by two accounts at once, so the author
  // is not always the profile it was collected from. Saying so is the honest
  // version of what once silently relabelled the whole profile.
  const collaborator =
    post?.ownerUsername && post.ownerUsername !== username ? post.ownerUsername : null

  return (
    <Dialog open={open && Boolean(post)} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[88vh] w-[min(56rem,calc(100vw-2rem))] max-w-none overflow-y-auto p-0">
        {post ? (
          <div className="grid gap-0 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            {/* --- media ------------------------------------------------ */}
            <div className="space-y-2 border-b border-border/15 p-5 md:border-b-0 md:border-r">
              <AnimatePresence mode="wait" initial={false}>
                <motion.div
                  key={url ?? 'none'}
                  initial={reduced ? false : { opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={reduced ? undefined : { opacity: 0 }}
                  transition={spring}
                >
                  <PostMedia url={url} type={current?.mediaType ?? post.mediaType} />
                </motion.div>
              </AnimatePresence>

              {media.length > 1 ? (
                <div className="flex flex-wrap items-center gap-1.5">
                  {media.map((item, index) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        setSlide(index)
                      }}
                      aria-label={`Show slide ${index + 1} of ${media.length}`}
                      aria-pressed={index === slide}
                      className={
                        'overflow-hidden rounded-md border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ' +
                        (index === slide
                          ? 'border-primary/60'
                          : 'border-border/20 hover:border-primary/35')
                      }
                    >
                      <SafeImage
                        src={mediaSrc(item.mediaUrl)}
                        alt=""
                        className="size-11 border-0"
                        compact
                      />
                    </button>
                  ))}
                </div>
              ) : null}
            </div>

            {/* --- everything else -------------------------------------- */}
            <div className="min-w-0 space-y-4 p-5">
              <DialogHeader>
                <DialogTitle className="text-base">@{username}</DialogTitle>
                <DialogDescription>
                  {post.postedAt ? `Posted ${formatDate(post.postedAt)}` : 'Date not published'}
                </DialogDescription>
              </DialogHeader>

              <div className="flex flex-wrap items-center gap-1.5">
                {post.mediaType ? <Badge variant="muted">{post.mediaType}</Badge> : null}
                {post.isSponsored ? <Badge variant="outline">Sponsored</Badge> : null}
                {collaborator ? (
                  <Badge variant="outline">Collaboration with @{collaborator}</Badge>
                ) : null}
                {post.locationName ? (
                  <Badge variant="muted">
                    <MapPin className="size-3" aria-hidden="true" />
                    {post.locationName}
                  </Badge>
                ) : null}
              </div>

              <p className="max-h-44 overflow-y-auto whitespace-pre-line text-sm leading-relaxed">
                {post.caption || 'No caption on this post.'}
              </p>

              <dl className="grid grid-cols-2 gap-x-4 gap-y-3 border-t border-border/15 pt-4">
                <Figure label="Likes" value={post.likeCount} />
                <Figure label="Comments" value={post.commentCount} />
                {post.videoViewCount !== null ? (
                  <Figure label="Video views" value={post.videoViewCount} />
                ) : null}
                <Figure label="Hashtags" value={post.hashtagCount} />
              </dl>

              {post.hashtags.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {post.hashtags.map((tag) => (
                    <Badge key={tag} variant="muted">
                      #{tag}
                    </Badge>
                  ))}
                </div>
              ) : null}

              <div className="border-t border-border/15 pt-4">
                <h3 className="font-display text-sm font-semibold">
                  Comments
                  {comments.length > 0 ? (
                    <span className="ml-1.5 font-sans text-xs font-normal text-muted-foreground">
                      {comments.length} collected
                    </span>
                  ) : null}
                </h3>

                {comments.length === 0 ? (
                  <p className="mt-2 text-sm text-muted-foreground">
                    No comments were collected for this post.
                  </p>
                ) : (
                  <ul className="mt-3 max-h-56 space-y-3 overflow-y-auto pr-1">
                    {comments.map((comment, index) => (
                      <motion.li
                        key={comment.id}
                        initial={reduced ? false : { opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ ...spring, delay: Math.min(index * 0.03, 0.24) }}
                        className="rounded-md border border-border/15 bg-card p-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="truncate text-sm font-medium">
                            {comment.commenterUsername ? `@${comment.commenterUsername}` : 'Someone'}
                          </span>
                          {comment.likeCount ? (
                            <span className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
                              <Heart className="size-3" aria-hidden="true" />
                              {comment.likeCount.toLocaleString()}
                            </span>
                          ) : null}
                        </div>
                        <p className="mt-1 whitespace-pre-line text-sm text-muted-foreground">
                          {comment.commentText}
                        </p>
                      </motion.li>
                    ))}
                  </ul>
                )}
              </div>

              {post.postUrl ? (
                <a
                  href={post.postUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-primary"
                >
                  Open on Instagram
                  <ArrowUpRight className="size-3" aria-hidden="true" />
                </a>
              ) : null}
            </div>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}

/** A post's image, or its video where the CDN gives us a playable one. */
function PostMedia({ url, type }: { url: string | null; type: string | null }) {
  if (!url) {
    return (
      <div className="flex aspect-square w-full items-center justify-center rounded-md border border-dashed border-border/25 bg-muted/25 text-sm text-muted-foreground">
        No media was collected for this post
      </div>
    )
  }

  if (isVideo(url, type)) {
    return (
      <video
        src={mediaSrc(url)}
        controls
        playsInline
        preload="metadata"
        className="aspect-square w-full rounded-md border border-border/15 bg-muted/25 object-contain"
      />
    )
  }

  return <SafeImage src={mediaSrc(url)} alt="" className="aspect-square w-full" loading="eager" />
}

export function isVideo(url: string, type: string | null): boolean {
  return (type ?? '').toLowerCase() === 'video' || /\.(mp4|mov|webm)(\?|$)/i.test(url)
}

function Figure({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium tabular-nums">
        {value === null ? '—' : value.toLocaleString()}
      </dd>
    </div>
  )
}
