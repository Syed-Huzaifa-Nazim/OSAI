import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, errorMessage } from '@/lib/api-client'
import { useAuthStore } from '@/stores/auth-store'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'

type UserRow = {
  id: string
  email: string
  verified: boolean
  is_admin: boolean
  created_at: string
  wallet?: { balance: number; reserved: number }
}
type Activity = { id: string; [key: string]: unknown }
type UserDetail = UserRow & {
  full_name?: string | null
  email_confirmed_at?: string | null
  last_sign_in_at?: string | null
  updated_at?: string | null
  ledger: Activity[]
  runs: Activity[]
  requests: Activity[]
  projects: Activity[]
}
type EmailType = 'account_verified' | 'verification' | 'password_setup' | 'token_update' | 'announcement' | 'custom'
type EmailRecord = { id: string; email_type: EmailType; subject: string; body: string; status: string; created_at: string; sent_at?: string | null }

const emailTemplates: Record<EmailType, { label: string; subject: string; body: string }> = {
  account_verified: { label: 'Welcome', subject: 'Welcome to OptiStratixAI', body: 'Your OptiStratixAI account is ready. We will send your password setup instructions when email delivery is enabled.' },
  verification: { label: 'Verification reminder', subject: 'Verify your OptiStratixAI account', body: 'Please verify your email address to start using OptiStratixAI. Verification instructions will follow when email delivery is enabled.' },
  password_setup: { label: 'Password setup', subject: 'Set up your OptiStratixAI password', body: 'Password setup instructions will follow when email delivery is enabled.' },
  token_update: { label: 'Token update', subject: 'Your OptiStratixAI tokens', body: 'There is an update to your OptiStratixAI token balance.' },
  announcement: { label: 'Announcement', subject: 'An update from OptiStratixAI', body: '' },
  custom: { label: 'Custom email', subject: '', body: '' },
}
const display = (value: unknown) => value == null || value === '' ? '—' : String(value)
const date = (value: unknown) => value ? new Date(String(value)).toLocaleString() : '—'

export function UsersManagement({ detailId, basePath = '/admin/users' }: { detailId?: string; basePath?: string }) {
  const navigate = useNavigate()
  const currentUser = useAuthStore((state) => state.user)
  const [rows, setRows] = useState<UserRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [query, setQuery] = useState('')
  const [role, setRole] = useState('all')
  const [verified, setVerified] = useState('all')
  const [page, setPage] = useState(1)
  const [newEmail, setNewEmail] = useState('')
  const [newName, setNewName] = useState('')
  const [newVerified, setNewVerified] = useState(false)
  const [busy, setBusy] = useState(false)
  const [detail, setDetail] = useState<UserDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')
  const [fullName, setFullName] = useState('')
  const [delta, setDelta] = useState(1)
  const [reason, setReason] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setRows(await api.get<UserRow[]>(`/admin/users?q=${encodeURIComponent(query)}`))
      setError('')
    } catch (cause) { setError(errorMessage(cause)) }
    finally { setLoading(false) }
  }, [query])
  useEffect(() => { void load() }, [load])
  useEffect(() => { setPage(1) }, [query, role, verified])
  useEffect(() => {
    if (!detailId) { setDetail(null); setDetailError(''); return }
    let active = true
    setDetailLoading(true)
    setDetail(null)
    setDetailError('')
    void api.get<UserDetail>(`/admin/users/${detailId}`)
      .then((record) => { if (active) { setDetail(record); setFullName(record.full_name ?? '') } })
      .catch((cause) => { if (active) setDetailError(errorMessage(cause)) })
      .finally(() => { if (active) setDetailLoading(false) })
    return () => { active = false }
  }, [detailId])

  const filtered = rows.filter((row) =>
    (role === 'all' || row.is_admin === (role === 'admin')) &&
    (verified === 'all' || row.verified === (verified === 'verified')))
  const pages = Math.max(1, Math.ceil(filtered.length / 25))
  const visible = filtered.slice((page - 1) * 25, page * 25)

  async function createUser() {
    if (!newName.trim() || !newEmail.trim()) return
    setBusy(true); setError(''); setMessage('')
    try {
      const result = await api.post<{ id: string; email_status: string }>('/admin/users', { email: newEmail.trim(), full_name: newName.trim(), verified: newVerified })
      setMessage(result.email_status === 'pending_provider'
        ? 'Account created. Onboarding email is queued; delivery waits for GCP mail integration.'
        : 'Account created, but its onboarding email could not be queued. Open the account and retry in the Email tab.')
      setNewEmail(''); setNewName(''); setNewVerified(false)
      await load()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { setBusy(false) }
  }
  async function update(action: () => Promise<unknown>, success: string) {
    if (!detailId) return
    setBusy(true); setDetailError(''); setMessage('')
    try {
      await action()
      setMessage(success)
      const record = await api.get<UserDetail>(`/admin/users/${detailId}`)
      setDetail(record)
      setFullName(record.full_name ?? '')
      await load()
    } catch (cause) { setDetailError(errorMessage(cause)) }
    finally { setBusy(false) }
  }
  async function removeUser() {
    if (!detailId || !window.confirm('Permanently delete this user and associated records?')) return
    setBusy(true); setDetailError('')
    try {
      await api.delete(`/admin/users/${detailId}`)
      navigate(basePath)
      setMessage('User deleted.')
      await load()
    } catch (cause) { setDetailError(errorMessage(cause)) }
    finally { setBusy(false) }
  }

  return <div className="space-y-5">
    {error && <p role="alert" className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{error}</p>}
    {message && <p role="status" className="rounded-xl border border-success/30 bg-success/5 p-3 text-sm text-success">{message}</p>}
    <Card className="flex flex-wrap items-end gap-3 p-4">
      <label className="min-w-56 flex-1 text-xs font-medium text-muted-foreground">Search accounts<Input className="mt-1" placeholder="Email or user ID" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
      <label className="text-xs font-medium text-muted-foreground">Role<select className="mt-1 flex h-10 rounded-md border border-border/30 bg-input/50 px-3 text-sm text-foreground" value={role} onChange={(event) => setRole(event.target.value)}><option value="all">All roles</option><option value="admin">Admins</option><option value="user">Users</option></select></label>
      <label className="text-xs font-medium text-muted-foreground">Verification<select className="mt-1 flex h-10 rounded-md border border-border/30 bg-input/50 px-3 text-sm text-foreground" value={verified} onChange={(event) => setVerified(event.target.value)}><option value="all">All</option><option value="verified">Verified</option><option value="unverified">Unverified</option></select></label>
      <Button variant="outline" onClick={() => void load()} disabled={loading}>Refresh</Button>
    </Card>
    <Card className="space-y-3 p-4">
      <div><h2 className="font-semibold">Create user</h2><p className="mt-1 text-xs text-muted-foreground">The account is created now. Its onboarding email stays queued until GCP mail delivery is connected; no password is generated or exposed.</p></div>
      <div className="flex flex-wrap items-end gap-3">
        <label className="min-w-48 flex-1 text-xs font-medium text-muted-foreground">Full name<Input className="mt-1" value={newName} onChange={(event) => setNewName(event.target.value)} maxLength={120} /></label>
        <label className="min-w-52 flex-1 text-xs font-medium text-muted-foreground">Email<Input className="mt-1" type="email" value={newEmail} onChange={(event) => setNewEmail(event.target.value)} maxLength={254} /></label>
        <label className="text-xs font-medium text-muted-foreground">Status<select className="mt-1 flex h-10 rounded-md border border-border/30 bg-input/50 px-3 text-sm text-foreground" value={newVerified ? 'verified' : 'unverified'} onChange={(event) => setNewVerified(event.target.value === 'verified')}><option value="unverified">Unverified</option><option value="verified">Verified</option></select></label>
        <Button disabled={busy || !newName.trim() || !newEmail.includes('@')} onClick={() => void createUser()}>Create user</Button>
      </div>
    </Card>
    <div className="flex flex-wrap justify-between gap-2 text-sm text-muted-foreground"><p>{loading ? 'Loading accounts…' : `${filtered.length} accounts`}</p><p>Select Open to inspect a user in a modal.</p></div>
    <Card className="overflow-x-auto">
      {loading ? <p className="p-8 text-center text-sm text-muted-foreground" role="status">Loading users…</p> :
        visible.length === 0 ? <p className="p-8 text-center text-sm text-muted-foreground">No users found.</p> :
        <table className="w-full min-w-[620px] text-left text-sm"><thead className="border-b bg-muted/30 text-xs uppercase tracking-wide text-muted-foreground"><tr><th scope="col" className="px-4 py-3">Account</th><th scope="col" className="px-4 py-3">Role</th><th scope="col" className="px-4 py-3">Verified</th><th scope="col" className="px-4 py-3">Tokens</th><th scope="col" className="px-4 py-3">Details</th></tr></thead><tbody>{visible.map((row) => <tr key={row.id} className="border-b border-border/30 last:border-0 hover:bg-muted/20"><td className="px-4 py-3 font-medium">{row.email}</td><td className="px-4 py-3"><Badge variant={row.is_admin ? 'default' : 'outline'}>{row.is_admin ? 'Admin' : 'User'}</Badge></td><td className="px-4 py-3"><Badge variant={row.verified ? 'success' : 'warning'}>{row.verified ? 'Verified' : 'Pending'}</Badge></td><td className="px-4 py-3">{display(row.wallet?.balance ?? 0)}</td><td className="px-4 py-3"><Link className="font-medium text-primary hover:underline" to={`${basePath}/${row.id}`}>Open →</Link></td></tr>)}</tbody></table>}
    </Card>
    {pages > 1 && <div className="flex items-center justify-end gap-3"><Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button><span className="text-sm text-muted-foreground">Page {page} of {pages}</span><Button variant="outline" size="sm" disabled={page === pages} onClick={() => setPage(page + 1)}>Next</Button></div>}

    <Dialog open={Boolean(detailId)} onOpenChange={(open) => { if (!open) navigate(basePath) }}>
      <DialogContent className="flex max-h-[92vh] w-[min(96vw,1100px)] max-w-none flex-col overflow-y-auto p-5 sm:p-7">
        <DialogHeader>
          <DialogTitle>User details — {display(detail?.email)}</DialogTitle>
          <DialogDescription>Account, activity, and email drafts for this user.</DialogDescription>
        </DialogHeader>
        {detailLoading && <p role="status" className="py-8 text-center text-sm text-muted-foreground">Loading user details…</p>}
        {detailError && <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">{detailError}</p>}
        {detail && <Tabs defaultValue="overview" className="min-w-0">
          <TabsList className="w-full justify-start overflow-x-auto"><TabsTrigger value="overview">Overview</TabsTrigger><TabsTrigger value="activity">Activity</TabsTrigger><TabsTrigger value="email">Email</TabsTrigger></TabsList>
          <TabsContent value="overview" className="space-y-5">
            <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {([['Full name', detail.full_name], ['Email', detail.email], ['User ID', detail.id], ['Role', detail.is_admin ? 'Admin' : 'User'], ['Verification', detail.verified ? 'Verified' : 'Pending'], ['Created', date(detail.created_at)], ['Email confirmed', date(detail.email_confirmed_at)], ['Last sign in', date(detail.last_sign_in_at)], ['Updated', date(detail.updated_at)], ['Available tokens', detail.wallet?.balance ?? 0], ['Reserved tokens', detail.wallet?.reserved ?? 0]] as [string, unknown][]).map(([name, value]) => <div key={name} className="min-w-0 rounded-xl bg-muted/30 p-3"><dt className="text-xs text-muted-foreground">{name}</dt><dd className="mt-1 break-words text-sm font-semibold">{display(value)}</dd></div>)}
            </dl>
            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="space-y-3 p-4"><h3 className="font-semibold">Account controls</h3><div className="flex gap-2"><Input aria-label="Full name" value={fullName} onChange={(event) => setFullName(event.target.value)} maxLength={120} /><Button variant="outline" disabled={busy || !fullName.trim()} onClick={() => void update(() => api.patch(`/admin/users/${detailId}`, { full_name: fullName.trim() }), 'Profile updated.')}>Save</Button></div><div className="flex flex-wrap gap-2"><Button variant="outline" disabled={busy || detailId === currentUser?.id} onClick={() => { if (window.confirm('Change this user’s admin access?')) void update(() => api.patch(`/admin/users/${detailId}`, { is_admin: !detail.is_admin }), 'Role updated.') }}>{detail.is_admin ? 'Remove admin access' : 'Grant admin access'}</Button><Button variant="destructive" disabled={busy || detailId === currentUser?.id} onClick={() => void removeUser()}>Delete user</Button></div></Card>
              <Card className="space-y-3 p-4"><h3 className="font-semibold">Adjust token balance</h3><p className="text-xs text-muted-foreground">A reason is required and the adjustment appears in the ledger.</p><div className="flex flex-wrap gap-2"><Input aria-label="Token adjustment" className="w-24" type="number" min={-1000} max={1000} value={delta} onChange={(event) => setDelta(Number(event.target.value))} /><Input aria-label="Adjustment reason" className="min-w-40 flex-1" placeholder="Reason" value={reason} onChange={(event) => setReason(event.target.value)} /><Button disabled={busy || !delta || Math.abs(delta) > 1000 || !reason.trim()} onClick={() => void update(() => api.post(`/admin/users/${detailId}/tokens`, { delta, reason: reason.trim() }), 'Balance adjusted.')}>Apply</Button></div></Card>
            </div>
          </TabsContent>
          <TabsContent value="activity" className="grid gap-4 lg:grid-cols-2">
            <ActivityList title="Projects" rows={detail.projects} fields={['brand_name', 'status', 'created_at']} />
            <ActivityList title="Token requests" rows={detail.requests} fields={['amount', 'status', 'created_at']} />
            <ActivityList title="Recent token activity" rows={detail.ledger} fields={['event', 'delta', 'balance_after', 'reason', 'created_at']} />
            <ActivityList title="Scrape runs" rows={detail.runs} fields={['project_id', 'status', 'created_at']} />
          </TabsContent>
          <TabsContent value="email"><UserEmailTab userId={detail.id} recipient={detail.email} /></TabsContent>
        </Tabs>}
      </DialogContent>
    </Dialog>
  </div>
}

function ActivityList({ title, rows = [], fields }: { title: string; rows?: Activity[]; fields: string[] }) {
  return <Card className="p-4"><h3 className="mb-3 font-semibold">{title} <Badge variant="outline">{rows.length}</Badge></h3>{rows.length ? <div className="max-h-64 space-y-2 overflow-y-auto">{rows.map((row) => <dl key={row.id} className="rounded-lg bg-muted/30 p-3 text-xs">{fields.map((field) => <div key={field} className="flex gap-2"><dt className="min-w-24 text-muted-foreground">{field.replaceAll('_', ' ')}</dt><dd className="break-all">{field.endsWith('_at') ? date(row[field]) : display(row[field])}</dd></div>)}</dl>)}</div> : <p className="text-sm text-muted-foreground">No records yet.</p>}</Card>
}

function UserEmailTab({ userId, recipient }: { userId: string; recipient: string }) {
  const [kind, setKind] = useState<EmailType>('custom')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [records, setRecords] = useState<EmailRecord[]>([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const load = useCallback(async () => {
    try { setRecords(await api.get<EmailRecord[]>(`/admin/users/${userId}/emails`)); setError('') }
    catch (cause) { setError(errorMessage(cause)) }
  }, [userId])
  useEffect(() => { void load() }, [load])
  async function queue() {
    if (!subject.trim() || !body.trim()) return
    setBusy(true); setError(''); setMessage('')
    try {
      await api.post(`/admin/users/${userId}/emails`, { email_type: kind, subject: subject.trim(), body: body.trim() })
      setMessage('Email saved to the outbox. It has not been sent; GCP mail delivery is pending.')
      await load()
    } catch (cause) { setError(errorMessage(cause)) }
    finally { setBusy(false) }
  }
  return <div className="space-y-5">
    <p className="rounded-lg border border-border bg-muted/30 p-3 text-sm">Recipient: <strong>{recipient}</strong>. Emails on this screen are drafts in a delivery queue. None are sent until GCP mail integration is configured.</p>
    {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
    {message && <p role="status" className="text-sm text-success">{message}</p>}
    <div className="grid gap-3">
      <label className="text-xs font-medium text-muted-foreground">Email type<select className="mt-1 flex h-10 w-full rounded-md border border-border/30 bg-input/50 px-3 text-sm text-foreground" value={kind} onChange={(event) => { const next = event.target.value as EmailType; setKind(next); setSubject(emailTemplates[next].subject); setBody(emailTemplates[next].body) }}>{Object.entries(emailTemplates).map(([value, template]) => <option key={value} value={value}>{template.label}</option>)}</select></label>
      <label className="text-xs font-medium text-muted-foreground">Subject<Input className="mt-1" maxLength={200} value={subject} onChange={(event) => setSubject(event.target.value)} /></label>
      <label className="text-xs font-medium text-muted-foreground">Message<Textarea className="mt-1 min-h-32" maxLength={10000} value={body} onChange={(event) => setBody(event.target.value)} /></label>
      <div><Button disabled={busy || !subject.trim() || !body.trim()} onClick={() => void queue()}>Save to outbox</Button></div>
    </div>
    <section><h3 className="mb-2 font-semibold">Email history</h3>{records.length ? <div className="space-y-2">{records.map((record) => <Card key={record.id} className="p-3 text-sm"><div className="flex flex-wrap justify-between gap-2"><span className="font-medium">{record.subject}</span><Badge variant={record.status === 'sent' ? 'success' : 'outline'}>{record.status === 'pending_provider' ? 'Awaiting GCP delivery' : record.status}</Badge></div><p className="mt-1 text-xs text-muted-foreground">{emailTemplates[record.email_type]?.label ?? record.email_type} · {date(record.created_at)}</p><p className="mt-2 whitespace-pre-wrap text-sm">{record.body}</p></Card>)}</div> : <p className="text-sm text-muted-foreground">No email drafts yet.</p>}</section>
  </div>
}
