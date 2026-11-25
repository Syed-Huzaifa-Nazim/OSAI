import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api, errorMessage } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useAuthStore } from '@/stores/auth-store'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { Logo } from '@/components/shared/logo'
import { Badge } from '@/components/ui/badge'
import { adminNav, resourceConfig, type ResourceName } from './resource-config'
import { UsersManagement } from './users-management'
import { formatDateTime, formatFieldLabel, formatFieldValue, formatIdentifier } from '@/lib/utils'

type Row = Record<string, unknown> & { id: string }
const label = (s: string) => formatFieldLabel(s.replaceAll('-', ' '))
const printable = (value: unknown) => value == null ? '—' : String(value).slice(0, 180)
const isResource = (name: string): name is ResourceName => name in resourceConfig
const fieldValue = (key: string, value: unknown) => formatFieldValue(key, value)

export default function AdminPortal() {
  useDocumentTitle('Admin portal')
  const user = useAuthStore((s) => s.user)
  const location = useLocation()
  const area = location.pathname.split('/')[2] || 'dashboard'
  const detailId = location.pathname.split('/')[3]
  const title = isResource(area) ? resourceConfig[area].title : area === 'dashboard' ? 'Overview' : label(area)
  const [access, setAccess] = useState<'loading' | 'allowed' | 'denied'>('loading')
  const [runs, setRuns] = useState(0)
  useEffect(() => {
    void api.get<{ completedRuns24h: number }>('/admin/me').then((r) => { setAccess('allowed'); setRuns(r.completedRuns24h) }).catch(() => setAccess('denied'))
  }, [user?.id])
  if (!user) return <p className="p-8">Please sign in to access this page.</p>
  if (access === 'loading') return <p className="p-8" role="status">Checking admin access…</p>
  if (access === 'denied') return <div className="p-8"><h1 className="text-xl font-semibold">Admin access required</h1><Link to="/app/dashboard" className="text-primary underline">Back to app</Link></div>
  return <div className="canvas-grain min-h-screen bg-background text-foreground md:flex">
    <aside className="relative z-10 border-b border-border/70 bg-card/90 p-4 shadow-sm backdrop-blur-xl md:sticky md:top-0 md:h-screen md:w-[260px] md:shrink-0 md:border-b-0 md:border-r md:px-3">
      <Link to="/admin" className="flex h-16 items-center px-2"><Logo /></Link>
      <div className="mx-2 rounded-lg border border-primary/20 bg-primary/5 px-3 py-2"><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-primary">Admin portal</p><p className="mt-1 text-xs text-muted-foreground">Management workspace</p></div>
      <nav className="mt-4 flex gap-3 overflow-x-auto md:block md:max-h-[calc(100vh-195px)] md:space-y-5 md:overflow-y-auto" aria-label="Admin management">
        {adminNav.map((group) => <div key={group.heading} className="flex shrink-0 gap-1 md:block">
          <p className="hidden px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground md:block">{group.heading}</p>
          {group.items.map((item) => <Link key={item.key} to={item.key === 'dashboard' ? '/admin' : `/admin/${item.key}`}
            aria-current={area === item.key ? 'page' : undefined}
            className={`block whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors ${area === item.key ? 'bg-primary/15 font-semibold text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`}>{item.title}</Link>)}
        </div>)}
      </nav><Link className="mx-3 mt-4 hidden text-sm text-primary hover:underline md:block" to="/app/dashboard">Return to user app</Link>
    </aside>
    <main className="relative z-10 mx-auto min-w-0 w-full max-w-[1400px] flex-1 px-4 py-7 sm:px-6 lg:px-8">
      <div className="mb-7 flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-5"><div><p className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Administration</p><h1 className="mt-1 font-display text-3xl font-bold tracking-tight">{title}</h1><p className="mt-1 text-sm text-muted-foreground">{isResource(area) ? resourceConfig[area].description : area === 'dashboard' ? 'Manage users, tokens, projects and platform records.' : area === 'users' ? 'Accounts, permissions and token balances.' : area === 'ledger' ? 'Auditable token activity across accounts.' : 'Review and respond to token requests.'}</p></div><span className="rounded-full border border-border bg-card px-3 py-1 text-sm text-muted-foreground">{user.email}</span></div>
      {runs >= 5 && <CostReminder runs={runs} />}
      {area === 'dashboard' ? <Dashboard /> : area === 'users' ? <UsersManagement detailId={detailId} /> :
        area === 'token-requests' ? <Requests /> : area === 'ledger' ? <Ledger /> :
        isResource(area) ? <Resources key={area} name={area} /> : <p role="alert">Admin page not found.</p>}
    </main>
  </div>
}

function CostReminder({ runs }: { runs: number }) {
  const key = `admin-cost-warning-${new Date().toISOString().slice(0, 10)}`
  const [dismissed, setDismissed] = useState(() => sessionStorage.getItem(key) === 'yes')
  if (dismissed) return null
  return <Card className="mb-5 flex items-start justify-between gap-4 border-amber-500/40 bg-amber-500/5 p-4 text-sm" role="status">
    <p>You completed {runs} billable scrapes in the last 24 hours. Extensive scraping and processing may increase Railway and other infrastructure usage costs.</p>
    <Button size="sm" variant="outline" onClick={() => { sessionStorage.setItem(key, 'yes'); setDismissed(true) }}>Dismiss</Button>
  </Card>
}

function useRows(path: string) {
  const [rows, setRows] = useState<Row[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const load = () => { setLoading(true); setError(''); void api.get<Row[]>(path).then(setRows).catch((e) => setError(errorMessage(e))).finally(() => setLoading(false)) }
  useEffect(load, [path])
  return { rows, error, setError, loading, load }
}

function Dashboard() {
  const [counts, setCounts] = useState<Record<string, number>>({})
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => { void api.get<Record<string, number>>('/admin/summary').then(setCounts).catch((e) => setError(errorMessage(e))).finally(() => setLoading(false)) }, [])
  const metrics = [
    { key: 'users', title: 'Users', to: '/admin/users', description: 'Registered accounts' },
    { key: 'projects', title: 'Projects', to: '/admin/projects', description: 'User analyses' },
    { key: 'requests', title: 'Token requests', to: '/admin/token-requests', description: 'Requests awaiting review or reviewed' },
    { key: 'runs', title: 'Token runs', to: '/admin/ledger', description: 'Recorded scrape reservations' },
    { key: 'contacts', title: 'Contact messages', to: '/admin/contacts', description: 'Public form submissions' },
  ]
  return <div className="space-y-8">
    {error && <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-destructive">{error}</p>}
    <section aria-label="Platform summary" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {metrics.map((metric) => <Link to={metric.to} key={metric.key} className="group rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
        <Card className="h-full p-5 transition-colors group-hover:border-primary/40"><p className="text-sm font-medium text-muted-foreground">{metric.title}</p><p className="mt-2 font-display text-4xl font-bold tracking-tight">{loading ? '…' : counts[metric.key] ?? '—'}</p><p className="mt-2 text-xs text-muted-foreground">{metric.description}</p><span className="mt-4 block text-sm font-semibold text-primary">Open {metric.title.toLowerCase()} →</span></Card>
      </Link>)}
    </section>
    <section><div className="mb-3 flex items-center justify-between"><h2 className="font-display text-xl font-semibold">Management areas</h2><Badge variant="outline">Admin only</Badge></div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{adminNav.slice(1).map((group) => <Card key={group.heading} className="p-5"><h3 className="font-semibold">{group.heading}</h3><div className="mt-3 flex flex-wrap gap-2">{group.items.map((item) => <Link key={item.key} to={`/admin/${item.key}`} className="rounded-lg border border-border/40 px-3 py-1.5 text-sm text-muted-foreground hover:border-primary/40 hover:text-primary">{item.title}</Link>)}</div></Card>)}</div>
    </section>
  </div>
}

function Requests() {
  const [status, setStatus] = useState('pending')
  const { rows, error, setError, loading, load } = useRows(`/admin/token-requests?status=${status}`)
  const [responses, setResponses] = useState<Record<string, string>>({})
  const [message, setMessage] = useState('')
  const [q, setQ] = useState('')
  const [busyId, setBusyId] = useState('')
  const matching = rows.filter((row) => !q || String(row.user_id).toLowerCase().includes(q.toLowerCase()) || String(row.note).toLowerCase().includes(q.toLowerCase()))
  async function review(id: string, approve: boolean) {
    setBusyId(id); setError(''); setMessage('')
    try { await api.post(`/admin/token-requests/${id}/review`, { approve, response: responses[id] || (approve ? 'Approved' : 'Rejected') }); setMessage(`Request ${approve ? 'approved' : 'rejected'}.`); load() } catch (e) { setError(errorMessage(e)) } finally { setBusyId('') }
  }
  return <div className="space-y-4"><Card className="flex flex-wrap items-end gap-3 p-4"><label className="min-w-52 flex-1 text-xs font-medium text-muted-foreground">Search requests<Input className="mt-1" placeholder="User ID or request note" value={q} onChange={(e) => setQ(e.target.value)} /></label><label className="text-xs font-medium text-muted-foreground">Status<select className="mt-1 flex h-10 rounded-md border border-border/30 bg-input/50 px-3 text-sm text-foreground" value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option><option>pending</option><option>approved</option><option>rejected</option></select></label><Button variant="outline" onClick={load} disabled={loading}>Refresh</Button></Card>
    {error && <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p>}{message && <p role="status" className="rounded-xl border border-success/30 bg-success/5 p-3 text-sm text-success">{message}</p>}
    <p className="text-sm text-muted-foreground">{loading ? 'Loading requests…' : `${matching.length} matching requests`}</p>
    {loading ? <Card className="p-8 text-center text-sm text-muted-foreground">Loading requests…</Card> : matching.length === 0 ? <Card className="p-10 text-center"><h2 className="font-semibold">No requests found</h2><p className="mt-1 text-sm text-muted-foreground">Try another search or status.</p></Card> : matching.map((r) => <Card key={r.id} className="space-y-3 p-5"><div className="flex flex-wrap items-start justify-between gap-2"><div><p className="font-semibold">{printable(r.amount)} tokens requested</p><Link className="text-sm text-primary hover:underline" to={`/admin/users/${r.user_id}`} title={String(r.user_id ?? "")}>View requester · {formatIdentifier(r.user_id)}</Link><p className="mt-1 text-xs text-muted-foreground">Requested {formatDateTime(r.created_at)}</p></div><Badge variant={r.status === 'approved' ? 'success' : r.status === 'rejected' ? 'destructive' : 'warning'}>{label(String(r.status))}</Badge></div><p className="rounded-lg bg-muted/30 p-3 text-sm">{printable(r.note)}</p>{r.status === 'pending' ? <><label className="block text-xs font-medium text-muted-foreground">Response to user<Textarea className="mt-1" placeholder="Explain the decision" value={responses[r.id] || ''} onChange={(e) => setResponses({ ...responses, [r.id]: e.target.value })} /></label><div className="flex gap-2"><Button loading={busyId === r.id} onClick={() => void review(r.id, true)}>Approve</Button><Button variant="outline" disabled={busyId === r.id} onClick={() => void review(r.id, false)}>Reject</Button></div></> : <p className="text-sm text-muted-foreground">Admin response: {printable(r.admin_response)}</p>}</Card>)}
  </div>
}

function Ledger() {
  const [q, setQ] = useState('')
  const [event, setEvent] = useState('')
  const [page, setPage] = useState(1)
  const { rows, error, loading, load } = useRows('/admin/ledger')
  const events = [...new Set(rows.map((row) => String(row.event)))].sort()
  const matching = rows.filter((row) => (!event || row.event === event) && (!q || String(row.user_id).toLowerCase().includes(q.toLowerCase())))
  const totalPages = Math.max(1, Math.ceil(matching.length / 25))
  const visible = matching.slice((page - 1) * 25, page * 25)
  useEffect(() => { setPage(1) }, [q, event])
  return <div className="space-y-4"><Card className="flex flex-wrap items-end gap-3 p-4"><label className="min-w-52 flex-1 text-xs font-medium text-muted-foreground">Filter by user ID<Input className="mt-1" placeholder="Paste user ID to search" value={q} onChange={(e) => setQ(e.target.value)} /></label><label className="text-xs font-medium text-muted-foreground">Event<select className="mt-1 flex h-10 rounded-md border border-border/30 bg-input/50 px-3 text-sm text-foreground" value={event} onChange={(e) => setEvent(e.target.value)}><option value="">All events</option>{events.map((item) => <option key={item}>{item}</option>)}</select></label><Button variant="outline" onClick={load} disabled={loading}>Refresh</Button></Card>{error && <p role="alert" className="text-destructive">{error}</p>}<p className="text-sm text-muted-foreground">{loading ? 'Loading activity…' : `${matching.length} matching entries`}</p>
    <Card className="overflow-x-auto">{loading ? <p className="p-8 text-center text-sm text-muted-foreground">Loading activity…</p> : visible.length === 0 ? <div className="p-10 text-center"><h2 className="font-semibold">No ledger entries</h2><p className="mt-1 text-sm text-muted-foreground">Try another user or event.</p></div> : <table className="w-full min-w-[760px] text-left text-sm"><thead className="border-b bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground"><tr><th scope="col" className="px-4 py-3">User</th><th scope="col" className="px-4 py-3">Event</th><th scope="col" className="px-4 py-3">Change</th><th scope="col" className="px-4 py-3">Balance</th><th scope="col" className="px-4 py-3">Reason</th><th scope="col" className="px-4 py-3">Date</th></tr></thead><tbody>{visible.map((r) => <tr key={r.id} className="border-b border-border/30 last:border-0"><td className="px-4 py-3"><Link className="text-primary hover:underline" to={`/admin/users/${r.user_id}`} title={String(r.user_id ?? "")}>Open user · {formatIdentifier(r.user_id)}</Link></td><td className="px-4 py-3">{label(String(r.event))}</td><td className="px-4 py-3 font-semibold">{Number(r.delta) > 0 ? '+' : ''}{printable(r.delta)}</td><td className="px-4 py-3">{printable(r.balance_after)}</td><td className="px-4 py-3">{printable(r.reason)}</td><td className="px-4 py-3">{formatDateTime(r.created_at)}</td></tr>)}</tbody></table>}</Card>
    {totalPages > 1 && <div className="flex items-center justify-end gap-3"><Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button><span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span><Button variant="outline" size="sm" disabled={page === totalPages} onClick={() => setPage(page + 1)}>Next</Button></div>}
  </div>
}

function Resources({ name }: { name: string }) {
  const meta = resourceConfig[name as ResourceName]
  const [q, setQ] = useState('')
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<Row | null>(null)
  const { rows, error, setError, loading, load } = useRows(`/admin/resources/${name}?q=${encodeURIComponent(q)}`)
  const [message, setMessage] = useState('')
  const [editing, setEditing] = useState<{ id: string; field: string; value: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const filterKey = 'filter' in meta ? meta.filter : undefined
  const options = filterKey ? [...new Set(rows.map((row) => String(row[filterKey] ?? '')).filter(Boolean))].sort() : []
  const matching = filterKey && filter ? rows.filter((row) => String(row[filterKey]) === filter) : rows
  const visible = matching.slice((page - 1) * 25, page * 25)
  const totalPages = Math.max(1, Math.ceil(matching.length / 25))
  useEffect(() => { setPage(1) }, [q, filter])

  async function save() {
    if (!editing || !editing.value.trim()) return
    setBusy(true); setError(''); setMessage('')
    try {
      await api.patch(`/admin/resources/${name}/${editing.id}`, { changes: { [editing.field]: editing.value.trim() } })
      setMessage(`${meta.title} record updated.`); setEditing(null); setSelected(null); load()
    } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) }
  }
  async function remove(id: string) {
    if (!window.confirm(`Permanently delete this ${meta.title.toLowerCase()} record? This may remove related data.`)) return
    setBusy(true); setError(''); setMessage('')
    try { await api.delete(`/admin/resources/${name}/${id}`); setMessage('Record deleted.'); setSelected(null); load() }
    catch (e) { setError(errorMessage(e)) } finally { setBusy(false) }
  }
  return <div className="space-y-5">
    <Card className="flex flex-wrap items-end gap-3 p-4">
      <label className="min-w-56 flex-1 text-xs font-medium text-muted-foreground">Search {meta.title.toLowerCase()}<Input className="mt-1" placeholder={`Search ${meta.title.toLowerCase()}`} value={q} onChange={(e) => setQ(e.target.value)} /></label>
      {filterKey && <label className="text-xs font-medium text-muted-foreground">{label(filterKey)}<select className="mt-1 flex h-10 min-w-40 rounded-md border border-border/30 bg-input/50 px-3 text-sm text-foreground" value={filter} onChange={(e) => setFilter(e.target.value)}><option value="">All</option>{options.map((option) => <option key={option}>{option}</option>)}</select></label>}
      <Button variant="outline" onClick={load} disabled={loading}>Refresh</Button>
    </Card>
    <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground"><p>{loading ? 'Loading records…' : `${matching.length} ${matching.length === 1 ? 'record' : 'records'} in the first ${rows.length} loaded`}</p><p>Search covers up to 200 matching records.</p></div>
    {error && <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p>}
    {message && <p role="status" className="rounded-xl border border-success/30 bg-success/5 p-3 text-sm text-success">{message}</p>}
    {editing && <Card className="flex flex-wrap items-end gap-3 p-4"><label className="min-w-56 flex-1 text-sm font-medium">Edit {label(editing.field)}<Input className="mt-1" value={editing.value} onChange={(e) => setEditing({ ...editing, value: e.target.value })} /></label><Button loading={busy} onClick={() => void save()}>Save</Button><Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button></Card>}
    <Card className="overflow-x-auto">{loading ? <p className="p-8 text-center text-sm text-muted-foreground" role="status">Loading {meta.title.toLowerCase()}…</p> : visible.length === 0 ? <div className="p-10 text-center"><h2 className="font-semibold">No {meta.title.toLowerCase()} found</h2><p className="mt-1 text-sm text-muted-foreground">Try another search or filter.</p></div> :
      <table className="w-full min-w-[760px] text-left text-sm"><thead className="border-b bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground"><tr>{meta.columns.map((key) => <th key={key} scope="col" className="px-4 py-3 font-semibold">{label(key)}</th>)}<th scope="col" className="px-4 py-3 font-semibold">Details</th></tr></thead><tbody>{visible.map((row) => <tr key={row.id} className="border-b border-border/30 last:border-0 hover:bg-muted/20">{meta.columns.map((key) => <td key={key} className="max-w-56 truncate px-4 py-3" title={fieldValue(key, row[key])}>{fieldValue(key, row[key])}</td>)}<td className="px-4 py-3"><Button size="sm" variant="outline" onClick={() => setSelected(row)}>Open</Button></td></tr>)}</tbody></table>}
    </Card>
    {totalPages > 1 && <div className="flex items-center justify-end gap-3"><Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button><span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span><Button variant="outline" size="sm" disabled={page === totalPages} onClick={() => setPage(page + 1)}>Next</Button></div>}
    {selected && <Card className="space-y-4 p-5"><div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-widest text-primary">{meta.title} record</p><h2 className="mt-1 font-display text-xl font-semibold">{printable(selected[meta.columns[0]])}</h2></div><Button variant="outline" size="sm" onClick={() => setSelected(null)}>Close</Button></div>
      <dl className="grid gap-3 sm:grid-cols-2">{Object.entries(selected).map(([key, value]) => <div key={key} className="rounded-lg bg-muted/30 p-3"><dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label(key)}</dt><dd className="mt-1 break-all text-sm">{fieldValue(key, value)}</dd></div>)}</dl>
      <div className="flex flex-wrap gap-2 border-t border-border/40 pt-4">{meta.edit.map((field) => <Button key={field} size="sm" variant="outline" onClick={() => { setEditing({ id: selected.id, field, value: String(selected[field] ?? '') }); window.scrollTo({ top: 0, behavior: 'smooth' }) }}>Edit {label(field)}</Button>)}{name !== 'reviews' && <Button size="sm" variant="destructive" disabled={busy} onClick={() => void remove(selected.id)}>Delete record</Button>}</div>
    </Card>}
  </div>
}
