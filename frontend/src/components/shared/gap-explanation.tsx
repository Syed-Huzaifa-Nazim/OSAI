import { Fragment, useRef } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Heart,
  ImageIcon,
  Lightbulb,
  MessageCircle,
  Play,
  RotateCcw,
  Sparkle,
  Trophy,
  UserRound,
  Users,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { SafeImage } from '@/components/shared/safe-image'
import { mediaSrc } from '@/lib/media'
import { cn } from '@/lib/utils'
import type { GapExplanation, KnowledgeFact } from '@/lib/api/services'
import type { GapDetails, SavedExplanation } from '@/types/domain'

type Evidence = GapExplanation['evidence'][number]

/** The explanation the backend saved on the gap, in the same shape as a fresh one. */
export function fromSaved(gapId: string, s: SavedExplanation): GapExplanation {
  return {
    gapId,
    explanation: s.explanation ?? '',
    found: s.found ?? '',
    why: s.why ?? '',
    general: s.general ?? '',
    knowledge: s.knowledge ?? [],
    knowledgeUsed: s.knowledge_used ?? [],
    grounded: Boolean(s.grounded),
    evidenceUsed: s.evidence_used ?? [],
    unknownCitations: s.unknown_citations ?? [],
    evidence: (s.evidence ?? []).map((e) => ({
      id: e.id,
      side: e.side,
      fieldType: 'post',
      text: e.text ?? '',
      postUrl: e.post_url ?? '',
      similarity: 1,
      format: e.format ?? '',
      date: e.date ?? null,
      likes: e.likes ?? null,
      comments: e.comments ?? null,
      retrieved: Boolean(e.retrieved),
      imageUrl: e.image_url ?? '',
    })),
  }
}

/** Text with [E1] shown as a small numbered circle (the post with that number) and [K1] as a tiny source link. */
function Cited({ text, knowledge }: { text: string; knowledge: KnowledgeFact[] }) {
  const parts = text.split(/(\[[EK]\d+\])/g)
  return (
    <>
      {parts.map((part, index) => {
        const match = /^\[([EK])(\d+)\]$/.exec(part)
        if (!match) return <span key={index}>{part}</span>
        if (match[1] === 'E') {
          return (
            <span
              key={index}
              className="mx-0.5 inline-flex size-4 items-center justify-center rounded-full bg-primary/15 align-middle text-[10px] font-semibold text-primary"
              aria-label={`post ${match[2]}`}
            >
              {match[2]}
            </span>
          )
        }
        const fact = knowledge.find((k) => k.id === `K${match[2]}`)
        return fact ? (
          <a
            key={index}
            href={fact.url}
            target="_blank"
            rel="noreferrer"
            title={fact.source}
            className="ml-0.5 align-super text-[10px] text-primary hover:underline"
          >
            source
          </a>
        ) : null
      })}
    </>
  )
}

/** "12 of 30" becomes a big "12 / 30"; other values ("yes", a list of hashtags) are shown as they are. */
function BigValue({ value }: { value: string }) {
  const match = /^(\d[\d,.]*)\s+of\s+(\d[\d,.]*)$/.exec(value.trim())
  if (match) {
    return (
      <p className="font-display text-3xl font-extrabold tabular-nums sm:text-4xl" aria-label={value}>
        {match[1]}
        <span className="mx-1.5 font-medium text-muted-foreground" aria-hidden="true">
          /
        </span>
        <span className="font-semibold" aria-hidden="true">
          {match[2]}
        </span>
      </p>
    )
  }
  const short = value.length <= 14
  return (
    <p className={cn('font-display font-bold', short ? 'text-2xl first-letter:uppercase sm:text-3xl' : 'text-sm leading-snug sm:text-base')}>
      {value}
    </p>
  )
}

const SIDE = {
  you: { name: 'You', icon: UserRound, tile: 'border-primary/15 from-card to-primary/10', badge: 'bg-primary/10 text-primary' },
  competitor: {
    name: 'Competitor',
    icon: Trophy,
    tile: 'border-warning/30 from-card to-warning/25',
    badge: 'bg-warning/25 text-warning-ink',
  },
  typical: { name: 'Jewellery shops usually', icon: Users, tile: 'border-border/25 from-card to-muted/60', badge: 'bg-muted text-foreground' },
} as const

function SideTile({
  who,
  value,
  label,
  daraz = false,
}: {
  who: keyof typeof SIDE
  value: string
  label: string
  daraz?: boolean
}) {
  const side = who === 'typical' && daraz ? { ...SIDE.typical, name: 'Top 20 listings' } : SIDE[who]
  return (
    <div
      className={cn(
        'relative flex min-w-0 flex-1 items-center gap-4 overflow-hidden rounded-2xl border bg-gradient-to-br p-4 sm:p-5',
        side.tile,
      )}
    >
      <svg viewBox="0 0 200 80" className="pointer-events-none absolute -bottom-1 right-0 h-16 w-48 opacity-60" aria-hidden="true">
        <path d="M0 80 C 60 70, 120 20, 200 10 L200 80 Z" className={who === 'competitor' ? 'fill-warning/30' : 'fill-primary/10'} />
      </svg>
      <span className={cn('relative flex size-14 shrink-0 items-center justify-center rounded-full shadow-sm', side.badge)}>
        <side.icon className={cn('size-7', who === 'competitor' && 'fill-warning')} aria-hidden="true" />
      </span>
      <div className="relative min-w-0">
        <p className="font-display text-base font-bold">{side.name}</p>
        <BigValue value={value} />
        <p className="text-sm text-muted-foreground">{label}</p>
      </div>
    </div>
  )
}

/** Each row of numbers as side-by-side tiles: you, the competitor and, when known, similar accounts. */
function CompareTiles({
  rows,
  daraz = false,
}: {
  rows: NonNullable<GapDetails['numbers']>
  daraz?: boolean
}) {
  return (
    <div className="space-y-3">
      {rows.map((row) => {
        const sides = (['you', 'competitor', 'typical'] as const).filter((key) => row[key])
        return (
          <div key={row.label} className="flex flex-col items-stretch sm:flex-row sm:items-center">
            {sides.map((key, index) => (
              <Fragment key={key}>
                {index > 0 ? (
                  <span className="relative z-10 -my-3 flex size-12 shrink-0 items-center justify-center self-center rounded-full bg-card font-display text-sm font-extrabold text-primary shadow-lg ring-4 ring-primary/10 sm:-mx-3 sm:my-0 sm:size-14 sm:text-base">
                    VS
                  </span>
                ) : null}
                <SideTile who={key} value={row[key] as string} label={row.label} daraz={daraz} />
              </Fragment>
            ))}
          </div>
        )
      })}
    </div>
  )
}

/** One post: its picture (a reel shows its cover frame with a play sign), its number when the explanation
 *  mentions it, whose it is, likes and comments. The whole card opens the post on Instagram. */
function PostCard({ item, cited }: { item: Evidence; cited: boolean }) {
  const number = item.id.replace(/^E/, '')
  const videoFile = /\.mp4(\?|$)/i.test(item.imageUrl ?? '')
  const isVideo = (item.format ?? '').startsWith('video') || videoFile
  const picture = item.imageUrl && !videoFile ? item.imageUrl : ''
  const Icon = isVideo ? Play : ImageIcon
  const body = (
    <>
      <div className="relative aspect-[4/3] overflow-hidden rounded-xl border border-border/20 bg-muted/40">
        {picture ? (
          <SafeImage
            src={mediaSrc(picture)}
            alt=""
            className="size-full border-0 transition-transform duration-300 group-hover:scale-105"
            fit="cover"
            compact
          />
        ) : (
          <span className="flex size-full items-center justify-center text-muted-foreground">
            <Icon className="size-6" aria-hidden="true" />
          </span>
        )}
        {isVideo && picture ? (
          <span className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
            <span className="flex size-9 items-center justify-center rounded-full bg-black/45 text-white backdrop-blur-sm">
              <Play className="ml-0.5 size-4 fill-current" />
            </span>
          </span>
        ) : null}
        {cited ? (
          <span className="absolute left-1.5 top-1.5 inline-flex size-5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground shadow">
            {number}
          </span>
        ) : null}
        <span
          className={cn(
            'absolute bottom-1.5 left-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold shadow-sm',
            item.side === 'you' ? 'bg-card text-primary' : 'bg-warning text-warning-foreground',
          )}
        >
          {item.side === 'you' ? 'You' : 'Competitor'}
        </span>
        {item.postUrl ? (
          <span className="absolute right-1.5 top-1.5 flex size-6 items-center justify-center rounded-full bg-card/90 text-primary opacity-0 shadow transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
            <ExternalLink className="size-3.5" aria-hidden="true" />
          </span>
        ) : null}
      </div>
      <div className="mt-1.5 flex items-center gap-3 px-0.5 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <Heart className="size-3" aria-hidden="true" />
          {item.likes == null ? '-' : item.likes.toLocaleString()}
        </span>
        <span className="inline-flex items-center gap-1">
          <MessageCircle className="size-3" aria-hidden="true" />
          {item.comments == null ? '-' : item.comments.toLocaleString()}
        </span>
        {item.postUrl ? <span className="ml-auto font-medium text-primary group-hover:underline">Open</span> : null}
      </div>
    </>
  )
  const box = 'group block w-40 shrink-0 snap-start rounded-xl sm:w-44'
  return item.postUrl ? (
    <a
      href={item.postUrl}
      target="_blank"
      rel="noreferrer"
      className={cn(box, 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring')}
      aria-label={`Open post ${number}`}
      title="Open this post"
    >
      {body}
    </a>
  ) : (
    <div className={box}>{body}</div>
  )
}

/** One piece of Daraz evidence: a buyer's review (as a quote) or a listing (its picture and text). */
function ReviewCard({ item, cited }: { item: Evidence; cited: boolean }) {
  const number = item.id.replace(/^E/, '')
  const review = item.format === 'review'
  const body = (
    <div className="flex h-full flex-col rounded-xl border border-border/20 bg-card p-3">
      <div className="flex items-center gap-1.5">
        {cited ? (
          <span className="inline-flex size-5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
            {number}
          </span>
        ) : null}
        <span
          className={cn(
            'rounded-full px-2 py-0.5 text-[10px] font-semibold',
            item.side === 'you' ? 'bg-primary/10 text-primary' : 'bg-warning/25 text-warning-ink',
          )}
        >
          {item.side === 'you' ? 'You' : 'Competitor'}
        </span>
        <span className="text-[10px] text-muted-foreground">{review ? 'Buyer review' : 'Listing'}</span>
      </div>
      {!review && item.imageUrl ? (
        <SafeImage src={mediaSrc(item.imageUrl)} alt="" className="mt-2 aspect-[4/3] w-full rounded-lg border-0" fit="cover" compact />
      ) : null}
      <p className="mt-2 line-clamp-5 text-xs leading-relaxed text-muted-foreground [overflow-wrap:anywhere]">
        {review ? `“${item.text}”` : item.text}
      </p>
      {item.postUrl ? <span className="mt-auto pt-2 text-xs font-medium text-primary group-hover:underline">Open on Daraz</span> : null}
    </div>
  )
  const box = 'group block w-56 shrink-0 snap-start rounded-xl'
  return item.postUrl ? (
    <a href={item.postUrl} target="_blank" rel="noreferrer" className={cn(box, 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring')}>
      {body}
    </a>
  ) : (
    <div className={box}>{body}</div>
  )
}

/** The real posts behind the gap in a sliding row; the ones the explanation mentions come first. */
function PostsStrip({ data, daraz = false }: { data: GapExplanation; daraz?: boolean }) {
  const strip = useRef<HTMLDivElement>(null)
  const cited = data.evidence.filter((e) => data.evidenceUsed.includes(e.id))
  const others = data.evidence.filter((e) => !data.evidenceUsed.includes(e.id))
  const posts = [...cited, ...others]
  const fromThem = posts.filter((e) => e.side !== 'you').length
  const fromYou = posts.length - fromThem
  const slide = (direction: 1 | -1) => {
    const el = strip.current
    if (el) el.scrollBy({ left: direction * el.clientWidth * 0.8, behavior: 'smooth' })
  }
  const arrow =
    'absolute top-[38%] z-10 hidden size-9 -translate-y-1/2 items-center justify-center rounded-full border border-border/30 bg-card text-primary shadow-md transition hover:bg-primary hover:text-primary-foreground sm:flex'

  return (
    <div className="rounded-2xl border border-border/20 bg-card/60 p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <ImageIcon className="size-5" aria-hidden="true" />
        </span>
        <div>
          <p className="font-display text-base font-bold">
            {daraz ? 'Reviews and listings behind this gap' : 'Posts behind this gap'}
          </p>
          <p className="text-sm text-muted-foreground">
            {[fromThem ? `${fromThem} from your competitor` : '', fromYou ? `${fromYou} from you` : '']
              .filter(Boolean)
              .join(', ')}
            {cited.length
              ? `. Numbered ${daraz ? 'ones' : 'posts'} are the ones mentioned above.`
              : '.'}
          </p>
        </div>
      </div>
      <div className="relative mt-4 sm:px-6">
        {posts.length > 3 ? (
          <button type="button" className={cn(arrow, 'left-0 -translate-x-1/2')} onClick={() => { slide(-1) }} aria-label="Previous posts">
            <ChevronLeft className="size-4" />
          </button>
        ) : null}
        <div ref={strip} className="flex snap-x gap-3 overflow-x-auto pb-1 [scrollbar-width:none]">
          {posts.map((item) =>
            daraz ? (
              <ReviewCard key={item.id} item={item} cited={data.evidenceUsed.includes(item.id)} />
            ) : (
              <PostCard key={item.id} item={item} cited={data.evidenceUsed.includes(item.id)} />
            ),
          )}
        </div>
        {posts.length > 3 ? (
          <button type="button" className={cn(arrow, 'right-0 translate-x-1/2')} onClick={() => { slide(1) }} aria-label="Next posts">
            <ChevronRight className="size-4" />
          </button>
        ) : null}
      </div>
    </div>
  )
}

/** Shown while the explanation is being written: the same shape, gently pulsing, with what is happening. */
export function GapExplanationLoading() {
  return (
    <div className="mt-5 space-y-4" role="status" aria-live="polite">
      <div className="relative overflow-hidden rounded-2xl border border-primary/15 bg-gradient-to-r from-primary/10 via-primary/5 to-card p-4 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-6">
          <span className="relative flex size-16 shrink-0 items-center justify-center rounded-full bg-warning/25 text-warning-ink sm:size-20">
            <span className="absolute inset-0 animate-ping rounded-full bg-warning/25" aria-hidden="true" />
            <Lightbulb className="relative size-8 fill-warning sm:size-10" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1 space-y-2.5 sm:border-l sm:border-primary/20 sm:pl-6">
            <p className="font-display text-lg font-bold text-primary">Writing your explanation…</p>
            <p className="text-sm text-muted-foreground">Reading what is behind this gap and checking every fact. This takes a few seconds.</p>
            <div className="space-y-2 pt-1" aria-hidden="true">
              <span className="block h-2.5 w-11/12 animate-pulse rounded-full bg-primary/15" />
              <span className="block h-2.5 w-4/5 animate-pulse rounded-full bg-primary/15 [animation-delay:150ms]" />
              <span className="block h-2.5 w-2/3 animate-pulse rounded-full bg-primary/15 [animation-delay:300ms]" />
            </div>
          </div>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2" aria-hidden="true">
        <span className="h-24 animate-pulse rounded-2xl bg-primary/5" />
        <span className="h-24 animate-pulse rounded-2xl bg-warning/10 [animation-delay:150ms]" />
      </div>
    </div>
  )
}

/** What the Explain button shows: the key insight, you against the competitor in numbers, and the real posts. */
export function GapExplanationPanel({
  data,
  values,
  unproven,
  onAgain,
  againLoading = false,
  daraz = false,
}: {
  data: GapExplanation
  values: NonNullable<GapDetails['numbers']>
  unproven?: boolean
  /** A Daraz gap: the evidence is buyers' reviews and listings, not posts. */
  daraz?: boolean
  /** Writes a fresh explanation. */
  onAgain?: () => void
  againLoading?: boolean
}) {
  const knowledge = data.knowledge ?? []

  return (
    <div className="mt-5 space-y-4">
      <div className="relative overflow-hidden rounded-2xl border border-primary/15 bg-gradient-to-r from-primary/10 via-primary/5 to-card p-4 sm:p-6">
        <svg viewBox="0 0 300 120" className="pointer-events-none absolute -bottom-2 right-0 h-28 w-72" aria-hidden="true">
          <path d="M40 120 C 140 110, 220 60, 300 20 L300 120 Z" className="fill-primary/10" />
          <path d="M190 120 C 240 100, 280 70, 300 40 L300 120 Z" className="fill-warning/40" />
        </svg>
        <Sparkle className="absolute right-5 top-5 hidden size-6 fill-warning text-warning sm:block" aria-hidden="true" />
        <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-6">
          <span className="flex size-16 shrink-0 items-center justify-center rounded-full bg-warning/25 text-warning-ink shadow-[0_0_0_8px_hsl(var(--warning)/0.12)] sm:size-20">
            <Lightbulb className="size-8 fill-warning sm:size-10" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1 sm:border-l sm:border-primary/20 sm:pl-6">
            <div className="flex flex-wrap items-center gap-2 pr-8">
              <p className="font-display text-lg font-bold text-primary sm:text-xl">Key insight</p>
              {data.grounded ? (
                <Badge variant="success">
                  {daraz ? 'Based on real Daraz reviews and listings' : 'Based on your real posts'}
                </Badge>
              ) : (
                <Badge variant="destructive">Treat with care</Badge>
              )}
            </div>
            <p className="mt-2 text-sm leading-relaxed sm:text-[0.95rem]">
              {data.found || data.why ? (
                <>
                  {data.found ? <Cited text={data.found} knowledge={knowledge} /> : null}
                  {data.found && data.why ? ' ' : null}
                  {data.why ? <Cited text={data.why} knowledge={knowledge} /> : null}
                </>
              ) : (
                <Cited text={data.explanation} knowledge={knowledge} />
              )}
            </p>
            {data.general ? (
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                <span className="font-semibold text-foreground">Why it can matter: </span>
                <Cited text={data.general} knowledge={knowledge} />
              </p>
            ) : null}
            {unproven ? (
              <p className="mt-2 text-xs font-medium text-warning-ink">
                {daraz
                  ? 'Your buyers say this, but not more often than your competitor’s buyers: worth fixing, not a proven gap.'
                  : 'Based on only a few posts, so this is an idea to try, not a sure result.'}
              </p>
            ) : null}
            {onAgain ? (
              <Button variant="ghost" size="sm" className="-ml-2 mt-2" loading={againLoading} onClick={onAgain}>
                <RotateCcw /> Explain again
              </Button>
            ) : null}
          </div>
        </div>
      </div>

      {values.length > 0 ? <CompareTiles rows={values} daraz={daraz} /> : null}

      {data.evidence.length > 0 ? <PostsStrip data={data} daraz={daraz} /> : null}

      {data.unknownCitations.length > 0 ? (
        <p className="text-xs text-destructive">
          Removed references to posts or facts that were never given: {data.unknownCitations.join(', ')}
        </p>
      ) : null}

    </div>
  )
}
