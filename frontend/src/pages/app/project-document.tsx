import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Download, FileText, Printer } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { PageHeader } from '@/components/shared/page-header'
import { EmptyState, ErrorState, LoadingState } from '@/components/shared/state-views'
import { DocumentStructureChart } from '@/components/charts/document-structure-chart'
import { useDocument } from '@/hooks/use-automation'
import { usePipeline } from '@/hooks/use-pipeline'
import { useProject } from '@/hooks/use-projects'
import { useProjectId } from '@/hooks/use-project-id'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { documentsApi } from '@/lib/api/services'
import { isDemoMode } from '@/lib/config'
import { errorMessage } from '@/lib/api-client'
import { formatDate } from '@/lib/utils'
import { spring, staggerContainer, staggerItem } from '@/lib/motion'
import type { DocumentFormat, StrategyDocument } from '@/types/domain'

/** Stage 8: the assembled strategy document, plus export. */
export default function DocumentPage() {
  const projectId = useProjectId()
  const project = useProject(projectId)
  const pipeline = usePipeline(projectId)
  const { data: document, isLoading, isError, error, refetch } = useDocument(projectId)

  useDocumentTitle(project.data ? `${project.data.brandName} · Document` : 'Document')

  const handleExport = (format: DocumentFormat, doc: StrategyDocument): void => {
    // Demo mode has no server to stream a file from, so markdown is assembled
    // and downloaded in the browser instead. PDF and DOCX need the backend.
    if (isDemoMode && format !== 'markdown') {
      toast.info('Export needs the backend', {
        description:
          'PDF and DOCX are rendered server-side. Markdown export works here in demo mode.',
      })
      return
    }

    if (format === 'markdown') {
      const body = `# ${doc.title}\n\n${doc.content}\n`
      const blob = new Blob([body], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = `${doc.title.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.md`
      anchor.click()
      URL.revokeObjectURL(url)
      toast.success('Markdown downloaded')
      return
    }

    window.open(documentsApi.exportUrl(projectId, format), '_blank', 'noopener')
  }

  if (isError) {
    return (
      <ErrorState
        message={errorMessage(error)}
        onRetry={() => {
          void refetch()
        }}
      />
    )
  }

  if (isLoading) return <LoadingState rows={5} />

  if (!document) {
    const generating = pipeline.data?.stages[8].status === 'running'
    return (
      <div className="space-y-7">
        <PageHeader
          eyebrow="Stage 8 · Execution-oriented output"
          title="Strategy document"
          description="The approved strategy, assembled into something you can hand to someone."
        />
        <EmptyState
          title={generating ? 'Assembling the document' : 'No document yet'}
          description={
            generating
              ? 'Sections are being written and formatted. This page fills in when stage 8 completes.'
              : 'The document is generated once you approve the strategy at the second human checkpoint.'
          }
          icon={<FileText className="size-5" />}
          action={
            <Button asChild variant="outline">
              <Link
                to={`/app/projects/${projectId}/${
                  pipeline.data?.blockedOn === 7 ? 'review-strategy' : 'pipeline'
                }`}
              >
                {pipeline.data?.blockedOn === 7 ? 'Approve the strategy' : 'Go to the pipeline'}
              </Link>
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Stage 8 · Execution-oriented output"
        title={document.title}
        description={`${document.wordCount.toLocaleString()} words · generated ${formatDate(document.generatedAt)}`}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => {
                window.print()
              }}
            >
              <Printer />
              Print
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button>
                  <Download />
                  Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {document.availableFormats.map((format) => (
                  <DropdownMenuItem
                    key={format}
                    onSelect={() => {
                      handleExport(format, document)
                    }}
                  >
                    {format === 'pdf' ? 'PDF' : format === 'docx' ? 'Word (DOCX)' : 'Markdown'}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        }
      />

      <DocumentStructureChart sections={document.sections} />

      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <nav aria-label="Document sections" className="lg:sticky lg:top-24 lg:self-start">
          <p className="eyebrow mb-3">Contents</p>
          <ol className="space-y-1">
            {document.sections.map((section) => (
              <li key={section.id}>
                <a
                  href={`#${section.id}`}
                  className="block rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground"
                >
                  {section.heading}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        <motion.article
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="space-y-5"
        >
          {document.sections
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((section) => (
              <motion.section key={section.id} id={section.id} variants={staggerItem}>
                <Card className="p-6 sm:p-7">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline">{String(section.order).padStart(2, '0')}</Badge>
                    <h2 className="font-display text-lg font-semibold">{section.heading}</h2>
                  </div>
                  <p className="mt-4 text-[15px] leading-relaxed text-muted-foreground">
                    {section.body}
                  </p>
                </Card>
              </motion.section>
            ))}

          <motion.div variants={staggerItem} transition={spring}>
            <Card glass className="p-6">
              <p className="eyebrow">Next</p>
              <h2 className="mt-1.5 font-display text-base font-semibold">
                Turn this into content
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Stage 9 maps each approved initiative to the blogs, SEO briefs, social posts and ad
                copy that would execute it.
              </p>
              <Button asChild className="mt-5">
                <Link to={`/app/projects/${projectId}/automation`}>Open automation</Link>
              </Button>
            </Card>
          </motion.div>
        </motion.article>
      </div>
    </div>
  )
}
