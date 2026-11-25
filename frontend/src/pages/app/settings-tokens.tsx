import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { PageHeader } from '@/components/shared/page-header'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { formatDateTime, formatFieldLabel } from '@/lib/utils'

interface Tokens {
  wallet: { balance: number; reserved: number; starter_awarded: boolean }
  ledger: { id: number; event: string; delta: number; balance_after: number; reason: string | null; created_at: string }[]
  requests: { id: string; amount: number; note: string; status: string; admin_response: string | null; created_at: string }[]
}

export default function TokenSettingsPage() {
  useDocumentTitle('Tokens')
  const [data, setData] = useState<Tokens | null>(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [amount, setAmount] = useState(1)
  const [note, setNote] = useState('')
  const [saving, setSaving] = useState(false)
  const [admin, setAdmin] = useState(false)
  const load = () => api.get<Tokens>('/tokens/me').then(setData).catch((e) => setError(errorMessage(e)))
  useEffect(() => {
    void load()
    void api.get('/admin/me').then(() => setAdmin(true)).catch(() => setAdmin(false))
  }, [])

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setSaving(true); setError(''); setMessage('')
    try {
      await api.post('/tokens/requests', { amount, note: note.trim() })
      setMessage('Request submitted for admin review.')
      setNote('')
      await load()
    } catch (e) { setError(errorMessage(e)) } finally { setSaving(false) }
  }

  return <div className="mx-auto max-w-3xl space-y-6">
    <PageHeader eyebrow="Settings" title="Tokens" description="One successfully completed scrape uses one token. Analysis and strategy steps use no additional tokens." />
    {admin && <Link className="text-primary underline" to="/admin">Open admin portal</Link>}
    {error && <p role="alert" className="text-destructive">{error}</p>}
    {message && <p role="status" className="text-primary">{message}</p>}
    <div className="grid gap-4 sm:grid-cols-2">
      <Card className="p-5"><p className="text-sm text-muted-foreground">Available</p><p className="text-3xl font-semibold">{data?.wallet.balance ?? '—'}</p></Card>
      <Card className="p-5"><p className="text-sm text-muted-foreground">Reserved for running scrapes</p><p className="text-3xl font-semibold">{data?.wallet.reserved ?? '—'}</p></Card>
    </div>
    <Card className="space-y-3 p-5"><h2 className="font-semibold">Request tokens</h2>
      <p className="text-sm text-muted-foreground">Requests are reviewed by an admin. No payment is collected here.</p>
      <form onSubmit={(e) => void submit(e)} className="space-y-3">
        <label className="block text-sm">Amount<Input type="number" min={1} max={1000} value={amount} onChange={(e) => setAmount(Number(e.target.value))} required /></label>
        <label className="block text-sm">Reason<Textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} required /></label>
        <Button disabled={saving || !note.trim()}>Submit request</Button>
      </form>
    </Card>
    <Card className="p-5"><h2 className="mb-3 font-semibold">Requests</h2>
      {!data ? <p>Loading…</p> : data.requests.length === 0 ? <p className="text-muted-foreground">No requests yet.</p> :
        <div className="space-y-2">{data.requests.map((r) => <div key={r.id} className="border-b py-2 text-sm">
          <strong>{r.amount} tokens · {formatFieldLabel(r.status)}</strong><p>{r.note}</p><p className="text-xs text-muted-foreground">Requested {formatDateTime(r.created_at)}</p>{r.admin_response && <p className="text-muted-foreground">Admin: {r.admin_response}</p>}
        </div>)}</div>}
    </Card>
    <Card className="p-5"><h2 className="mb-3 font-semibold">Usage history</h2>
      {!data ? <p>Loading…</p> : data.ledger.length === 0 ? <p className="text-muted-foreground">No token activity yet.</p> :
        <div className="space-y-2">{data.ledger.map((row) => <div key={row.id} className="flex justify-between gap-3 border-b py-2 text-sm">
          <span>{formatFieldLabel(row.event)}{row.reason ? ` · ${row.reason}` : ''}<span className="mt-1 block text-xs text-muted-foreground">{formatDateTime(row.created_at)}</span></span><span>{row.delta > 0 ? '+' : ''}{row.delta} · {row.balance_after} left</span>
        </div>)}</div>}
    </Card>
  </div>
}
