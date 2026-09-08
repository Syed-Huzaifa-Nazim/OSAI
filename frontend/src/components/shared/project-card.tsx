import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowUpRight, Building2, Radar, Trash2 } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { ProjectStatusBadge } from './project-status-badge'
import { DemoBadge } from './demo-badge'
import type { Project } from '@/types/domain'
import { getStage } from '@/lib/pipeline-stages'
import { formatRelative, titleCase } from '@/lib/utils'
import { staggerItem } from '@/lib/motion'

interface ProjectCardProps {
  project: Project
  onDelete?: (project: Project) => void
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const stage = getStage(project.currentStage)
  const progress = Math.round((project.currentStage / 9) * 100)

  return (
    <motion.div variants={staggerItem} whileHover={{ y: -3 }} className="h-full">
      <Card glass className="flex h-full flex-col p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate font-display text-base font-semibold">
                {project.brandName}
              </h3>
              {project.isDemo ? <DemoBadge compact /> : null}
            </div>
            <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
              <Building2 className="size-3" />
              {titleCase(project.industry)}
              <span aria-hidden="true">·</span>
              <Radar className="size-3" />
              {project.competitorCount} competitor{project.competitorCount === 1 ? '' : 's'}
            </p>
          </div>
          <ProjectStatusBadge status={project.status} />
        </div>

        <p className="mt-3 line-clamp-2 flex-1 text-sm text-muted-foreground">
          {project.brandDescription}
        </p>

        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">
              Stage {project.currentStage} · {stage.title}
            </span>
            <span className="font-mono tabular-nums text-muted-foreground">{progress}%</span>
          </div>
          <Progress value={progress} />
        </div>

        <div className="mt-4 flex items-center justify-between gap-2 border-t border-border/15 pt-4">
          <div className="flex items-center gap-2">
            {project.gapCount > 0 ? (
              <Badge variant="outline">{project.gapCount} gaps</Badge>
            ) : null}
            <span className="text-xs text-muted-foreground">
              {formatRelative(project.updatedAt)}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {onDelete ? (
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => {
                  onDelete(project)
                }}
                aria-label={`Delete ${project.brandName}`}
              >
                <Trash2 />
              </Button>
            ) : null}
            <Button asChild size="sm" variant="outline">
              <Link to={`/app/projects/${project.id}/pipeline`}>
                Open
                <ArrowUpRight />
              </Link>
            </Button>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
