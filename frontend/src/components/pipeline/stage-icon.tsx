import {
  Database,
  FileText,
  Lightbulb,
  ListChecks,
  PencilLine,
  Radar,
  ShieldCheck,
  Sparkles,
  Swords,
  type LucideIcon,
} from 'lucide-react'

/**
 * Icon names come from PIPELINE_STAGES as strings; this is the only place they
 * are resolved to components, so the stage table stays free of imports.
 */
const ICONS: Record<string, LucideIcon> = {
  PencilLine,
  Radar,
  Database,
  Lightbulb,
  ListChecks,
  Swords,
  ShieldCheck,
  FileText,
  Sparkles,
}

export function resolveStageIcon(name: string): LucideIcon {
  return ICONS[name] ?? Sparkles
}
