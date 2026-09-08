import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Compass } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Logo } from '@/components/shared/logo'
import { spring } from '@/lib/motion'
import { useDocumentTitle } from '@/hooks/use-document-title'

export default function NotFoundPage() {
  useDocumentTitle('Page not found')

  return (
    <div className="canvas-grain flex min-h-screen flex-col bg-background">
      <div className="relative z-10 p-6">
        <Link to="/">
          <Logo />
        </Link>
      </div>

      <div className="relative z-10 flex flex-1 items-center justify-center px-5 pb-20">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={spring}
          className="max-w-md text-center"
        >
          <span className="mx-auto mb-6 flex size-14 items-center justify-center rounded-full bg-primary/12 text-primary">
            <Compass className="size-6" />
          </span>
          <p className="eyebrow">Error 404</p>
          <h1 className="mt-3 font-display text-3xl font-semibold tracking-tight">
            This page is not on the map
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            The link may be out of date, or the analysis you were looking for has been deleted.
            Nothing has gone wrong with your account.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Button asChild>
              <Link to="/">
                <ArrowLeft />
                Back to home
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/app/dashboard">Go to dashboard</Link>
            </Button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
