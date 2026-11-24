import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { PageHeader } from '@/components/shared/page-header'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { api } from '@/lib/api-client'
import { useAuthStore } from '@/stores/auth-store'
import { UsersManagement } from '@/pages/admin/users-management'

export default function AdminUsersPage() {
  useDocumentTitle('Users')
  const { userId } = useParams()
  const user = useAuthStore((state) => state.user)
  const [access, setAccess] = useState<'loading' | 'allowed' | 'denied'>('loading')

  useEffect(() => {
    let active = true
    setAccess('loading')
    void api.get<{ isAdmin: boolean }>('/admin/me')
      .then((result) => { if (active) setAccess(result.isAdmin ? 'allowed' : 'denied') })
      .catch(() => { if (active) setAccess('denied') })
    return () => { active = false }
  }, [user?.id])

  return (
    <div className="mx-auto max-w-6xl space-y-7">
      <PageHeader eyebrow="Administration" title="Users" description="View and manage registered accounts, permissions, and token balances." />
      {access === 'loading' ? <p role="status" className="text-sm text-muted-foreground">Checking admin access…</p> : null}
      {access === 'denied' ? <p role="alert" className="text-sm text-destructive">Admin access required. <Link to="/app/dashboard" className="underline">Return to dashboard</Link></p> : null}
      {access === 'allowed' ? <UsersManagement detailId={userId} basePath="/app/users" /> : null}
    </div>
  )
}
