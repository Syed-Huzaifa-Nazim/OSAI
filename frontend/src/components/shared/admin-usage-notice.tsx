import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api-client'
import { Button } from '@/components/ui/button'

/** Informational cost reminder after five completed scrapes in 24 hours. */
export function AdminUsageNotice() {
  const [runs, setRuns] = useState(0)
  const key = `admin-usage-dismissed-${new Date().toISOString().slice(0, 10)}`
  const [hidden, setHidden] = useState(() => sessionStorage.getItem(key) === 'yes')
  useEffect(() => { void api.get<{ completedRuns24h: number }>('/admin/me').then((data) => setRuns(data.completedRuns24h)).catch(() => {}) }, [])
  if (runs < 5 || hidden) return null
  return <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 text-sm" role="status">
    <span>You completed {runs} billable scrapes in the last 24 hours. Extensive scraping and processing may increase Railway and other infrastructure usage costs. <Link to="/admin" className="text-primary underline">View admin usage</Link></span>
    <Button size="sm" variant="outline" onClick={() => { sessionStorage.setItem(key, 'yes'); setHidden(true) }}>Dismiss</Button>
  </div>
}
