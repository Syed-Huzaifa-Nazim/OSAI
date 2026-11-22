import { BarChart3, Brain, Film, Hash, ImageIcon, MessageSquareText, ThumbsUp, Users } from 'lucide-react'
import type { ReactNode } from 'react'
import { Card } from '@/components/ui/card'
import type { AnalysisPart, GradeDrivers, ResultsSide } from '@/types/pipeline'

const mix = (shares: Record<string, number> | undefined) =>
  shares && Object.keys(shares).length > 0
    ? Object.entries(shares)
        .sort((a, b) => b[1] - a[1])
        .map(([format, share]) => `${format} ${Math.round(share * 100)}%`)
        .join(', ')
    : 'not enough information'

const themes = (shares: Record<string, number> | undefined) =>
  shares && Object.keys(shares).length > 0
    ? Object.entries(shares)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([name, share]) => `${name} (${Math.round(share * 100)}%)`)
        .join(', ')
    : 'none could be read'

const signed = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(1)}`

/** One account's SHAP breakdown: start, top habits, everything else, final. */
function Drivers({ title, d }: { title: string; d: GradeDrivers }) {
  return (
    <div className="min-w-0 flex-1 rounded-md border border-border/20 p-2.5 text-xs">
      <p className="mb-1.5 font-medium text-foreground">{title}</p>
      <div className="flex justify-between text-muted-foreground">
        <span>Average account</span>
        <span>{d.start.toFixed(1)}%</span>
      </div>
      {d.items.map((item) => (
        <div key={item.label} className="flex justify-between gap-2">
          <span className="min-w-0 truncate">
            {item.label} <span className="text-muted-foreground">({item.value_text})</span>
          </span>
          <span className={item.points >= 0 ? 'shrink-0 text-emerald-500' : 'shrink-0 text-red-400'}>
            {signed(item.points)}
          </span>
        </div>
      ))}
      <div className="flex justify-between text-muted-foreground">
        <span>All other features</span>
        <span>{signed(d.others_points)}</span>
      </div>
      <div className="mt-1 flex justify-between border-t border-border/20 pt-1 font-medium">
        <span>Chance of &quot;good&quot;</span>
        <span>{d.final.toFixed(1)}%</span>
      </div>
    </div>
  )
}

function Row({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <div className="flex gap-3 border-t border-border/15 py-3 first:border-t-0 first:pt-0">
      <span className="mt-0.5 text-muted-foreground">{icon}</span>
      <div className="min-w-0 flex-1 space-y-1 text-sm">
        <p className="font-medium">{title}</p>
        {children}
      </div>
    </div>
  )
}

const side = (label: string, s: ResultsSide) =>
  `${label}: more likes and comments than ${Math.round(s.percentile)}% of accounts your size (from ${s.posts} posts)`

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

/** How the gaps were found, in plain words, with the technical detail tucked away. */
export function AnalysisSummary({ parts }: { parts: AnalysisPart[] }) {
  return (
    <>
      {parts.map((part) => {
        const r = part.results
        const verdict =
          r?.context === 'behind'
            ? `@${part.competitor} is doing better than you compared with similar accounts.`
            : r?.context === 'ahead'
              ? `You are doing better than @${part.competitor} compared with similar accounts, so differences below are things to test, not problems.`
              : r?.context === 'even'
                ? `You and @${part.competitor} are doing about equally well compared with similar accounts.`
                : null
        const m = part.model
        return (
          <Card key={part.competitor} className="space-y-1 p-5">
            <p className="mb-3 font-display text-sm font-semibold">
              How your gaps were found: you vs @{part.competitor}
            </p>

            <Row icon={<BarChart3 className="size-4" />} title="How your results compare">
              {r?.status === 'ran' && r.user && r.competitor ? (
                <>
                  <p className="text-muted-foreground">{side('You', r.user)}</p>
                  <p className="text-muted-foreground">{side(`@${part.competitor}`, r.competitor)}</p>
                  {verdict ? <p>{verdict}</p> : null}
                  <p className="text-xs text-muted-foreground">
                    Compared with {r.peers} real business accounts with a similar number of followers.
                  </p>
                </>
              ) : (
                <p className="text-muted-foreground">{r?.reason ?? 'Not available for this project.'}</p>
              )}
            </Row>

            <Row icon={<Users className="size-4" />} title="Habits">
              {part.habits?.status === 'ran' ? (
                <>
                  {part.habits.table && part.habits.table.length > 0 ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead className="text-muted-foreground">
                          <tr>
                            <th className="py-1 pr-3 font-medium">Habit</th>
                            <th className="py-1 pr-3 font-medium">You</th>
                            <th className="py-1 pr-3 font-medium">@{part.competitor}</th>
                            <th className="py-1 font-medium">Most accounts your size</th>
                          </tr>
                        </thead>
                        <tbody>
                          {part.habits.table.map((row) => (
                            <tr key={row.label} className="border-t">
                              <td className="py-1 pr-3">{row.label}</td>
                              <td className="py-1 pr-3">{row.you}</td>
                              <td className="py-1 pr-3">{row.competitor}</td>
                              <td className="py-1 text-muted-foreground">{row.typical ?? '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : null}
                  <p className="text-xs text-muted-foreground">
                    For comparison only, not advice: in the real accounts we studied, none of these habits clearly led
                    to more likes and comments.
                    {part.habits.gaps > 0
                      ? ` ${part.habits.gaps} profile item${part.habits.gaps === 1 ? '' : 's'} added as a gap.`
                      : ''}
                  </p>
                </>
              ) : (
                <p className="text-muted-foreground">{part.habits?.reason ?? 'Not available for this project.'}</p>
              )}
            </Row>

            <Row icon={<Film className="size-4" />} title="Types of post">
              {part.formats ? (
                <>
                  <p className="text-muted-foreground">You: {mix(part.formats.user)}</p>
                  <p className="text-muted-foreground">
                    @{part.competitor}: {mix(part.formats.competitor)}
                  </p>
                  <p>
                    {plural(part.formats.gaps ?? 0, 'clear difference')},{' '}
                    {plural(part.formats.worth_testing ?? 0, 'difference')} worth testing, and{' '}
                    {plural(part.formats.weak_spots ?? 0, 'weak spot')} in your own posts.
                  </p>
                </>
              ) : (
                <p className="text-muted-foreground">Not available for this project.</p>
              )}
            </Row>

            <Row icon={<MessageSquareText className="size-4" />} title="What the posts are about">
              {part.topics?.status === 'ran' ? (
                <>
                  <p className="text-muted-foreground">
                    We could read the topic of {part.topics.coverage?.user} of your posts and{' '}
                    {part.topics.coverage?.competitor} of @{part.competitor}&apos;s.
                  </p>
                  <p className="text-muted-foreground">You post most about: {themes(part.topics.topics?.user)}</p>
                  <p className="text-muted-foreground">
                    @{part.competitor} posts most about: {themes(part.topics.topics?.competitor)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    The topic model was trained on English captions, so posts in other languages are left out.
                  </p>
                </>
              ) : (
                <p className="text-muted-foreground">{part.topics?.reason || 'Not available for this project.'}</p>
              )}
            </Row>

            <Row icon={<Hash className="size-4" />} title="Hashtags">
              <p>
                {(part.topics?.hashtag_gaps ?? 0) > 0
                  ? 'Some of their hashtags clearly go with stronger posts, and you do not use them.'
                  : (part.topics?.hashtag_worth_testing ?? 0) > 0
                    ? 'Some of their hashtags may work better for them. Not proven yet, so they are listed as worth testing.'
                    : 'None of their hashtags clearly works better than their other posts.'}
              </p>
            </Row>

            <Row icon={<ImageIcon className="size-4" />} title="Pictures and videos">
              {part.media?.status === 'ran' ? (
                <>
                  <p className="text-muted-foreground">
                    Checked {part.media.scored?.user.scored ?? 0} of your {part.media.scored?.user.posts ?? 0} posts and{' '}
                    {part.media.scored?.competitor.scored ?? 0} of their {part.media.scored?.competitor.posts ?? 0}
                    {part.media.scored && part.media.scored.user.failed + part.media.scored.competitor.failed > 0
                      ? '. The rest could not be checked (some links had expired, or videos cannot be scored yet).'
                      : '.'}
                  </p>
                  {Object.values(part.media.models ?? {}).some((model) => !model.available) ? (
                    <p className="text-xs text-muted-foreground">
                      Not ready yet:{' '}
                      {Object.values(part.media.models ?? {})
                        .filter((model) => !model.available)
                        .map((model) => model.label.toLowerCase())
                        .join(', ')}
                      .
                    </p>
                  ) : null}
                  <details className="text-xs text-muted-foreground">
                    <summary className="cursor-pointer select-none">How the scores are made</summary>
                    {Object.values(part.media.models ?? {})
                      .filter((model) => model.available)
                      .map((model) => (
                        <p key={model.label} className="mt-1">
                          {model.label}: {model.description}. Trained on {model.trained_on} ({model.n_train} items rated
                          by people). On ratings it had not seen it agreed with people at {model.srcc?.toFixed(2)}
                          {model.baseline_srcc != null
                            ? `, against ${model.baseline_srcc.toFixed(2)} for simple measurements alone`
                            : ''}
                          .
                        </p>
                      ))}
                  </details>
                </>
              ) : (
                <p className="text-muted-foreground">
                  {part.media?.reason || 'Picture and video scoring is not available for this project.'}
                </p>
              )}
            </Row>

            <Row icon={<ThumbsUp className="size-4" />} title="What works for you">
              {part.strengths && part.strengths.length > 0 ? (
                <ul className="space-y-1">
                  {part.strengths.map((item) => (
                    <li key={`${item.kind}-${item.label}`}>
                      <span className="font-medium">{item.label}.</span>{' '}
                      <span className="text-muted-foreground">{item.detail}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground">Nothing stood out yet as clearly better than your other posts.</p>
              )}
            </Row>

            {m?.status === 'ran' && m.user_drivers && m.competitor_drivers ? (
              <details className="pt-3 text-xs text-muted-foreground">
                <summary className="flex cursor-pointer select-none items-center gap-2 font-medium">
                  <Brain className="size-3.5" /> Technical details: the trained grader
                </summary>
                <p className="mt-2">
                  A Random Forest trained on 997 real accounts grades each account from its habits. This is shown for
                  transparency and does not decide which gaps appear. Every account starts at the average chance of
                  being &quot;good&quot;; each habit then adds or removes points. You: {m.user_grade}, @
                  {part.competitor}: {m.competitor_grade}.
                </p>
                <div className="mt-2 flex flex-col gap-2 sm:flex-row">
                  <Drivers title="You" d={m.user_drivers} />
                  <Drivers title={`@${part.competitor}`} d={m.competitor_drivers} />
                </div>
              </details>
            ) : null}
          </Card>
        )
      })}
    </>
  )
}
