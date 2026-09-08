import { useNavigate } from 'react-router-dom'
import { useFieldArray, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { motion } from 'framer-motion'
import { ArrowRight, Info, Plus, Radar, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { FormField } from '@/components/ui/form-field'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PageHeader } from '@/components/shared/page-header'
import { useCreateProject } from '@/hooks/use-projects'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { newProjectSchema, type NewProjectValues } from '@/lib/validation'
import { titleCase } from '@/lib/utils'
import { spring, staggerContainer, staggerItem } from '@/lib/motion'
import type { Industry, SocialHandle } from '@/types/domain'

const INDUSTRIES: Industry[] = [
  'saas',
  'ecommerce',
  'fintech',
  'healthcare',
  'education',
  'hospitality',
  'agency',
  'manufacturing',
  'other',
]

/** Stage 1: everything the Scout and Insight agents need before they start. */
export default function NewProjectPage() {
  useDocumentTitle('New analysis')
  const navigate = useNavigate()
  const createProject = useCreateProject()

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<NewProjectValues>({
    resolver: zodResolver(newProjectSchema),
    defaultValues: {
      brandName: '',
      brandWebsite: '',
      brandDescription: '',
      industry: 'saas',
      targetAudience: '',
      objectives: [''],
      competitors: [{ name: '', landingPageUrl: '', instagram: '', linkedin: '', notes: '' }],
    },
  })

  const competitors = useFieldArray({ control, name: 'competitors' })
  const objectives = watch('objectives')
  const industry = watch('industry')

  const onSubmit = handleSubmit((values) => {
    createProject.mutate(
      {
        brandName: values.brandName,
        brandWebsite: values.brandWebsite || null,
        brandDescription: values.brandDescription,
        industry: values.industry,
        targetAudience: values.targetAudience,
        objectives: values.objectives.filter((objective) => objective.trim().length > 0),
        competitors: values.competitors.map((competitor) => {
          const socialHandles: SocialHandle[] = []
          if (competitor.instagram) {
            socialHandles.push({ platform: 'instagram', handle: competitor.instagram })
          }
          if (competitor.linkedin) {
            socialHandles.push({ platform: 'linkedin', handle: competitor.linkedin })
          }
          return {
            name: competitor.name,
            landingPageUrl: competitor.landingPageUrl,
            socialHandles,
            notes: competitor.notes || null,
          }
        }),
      },
      {
        onSuccess: (project) => {
          navigate(`/app/projects/${project.id}/pipeline`)
        },
      },
    )
  })

  return (
    <div className="mx-auto max-w-3xl space-y-7">
      <PageHeader
        eyebrow="Stage 1 · User input"
        title="New analysis"
        description="What the agents know about you is what you tell them here. The more specific this is, the less generic everything downstream will be."
      />

      <Card className="flex items-start gap-3 border-primary/25 bg-primary/5 p-4">
        <Info className="mt-0.5 size-4 shrink-0 text-primary" />
        <p className="text-sm text-muted-foreground">
          Nothing runs until you press start on the next screen. You can review and edit this before
          the Scout Agent touches anything.
        </p>
      </Card>

      <form onSubmit={onSubmit} className="space-y-6" noValidate>
        {/* ------------------------------------------------------- brand */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={spring}>
          <Card className="space-y-5 p-6">
            <div>
              <h2 className="font-display text-base font-semibold">Your brand</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                The subject of the analysis: the business the gaps will be measured against.
              </p>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <FormField
                label="Brand name"
                htmlFor="brandName"
                error={errors.brandName?.message}
                required
              >
                <Input
                  id="brandName"
                  placeholder="Verdant Roast"
                  aria-invalid={Boolean(errors.brandName)}
                  {...register('brandName')}
                />
              </FormField>

              <FormField
                label="Website"
                htmlFor="brandWebsite"
                error={errors.brandWebsite?.message}
                hint="Optional"
              >
                <Input
                  id="brandWebsite"
                  placeholder="https://yourbrand.com"
                  aria-invalid={Boolean(errors.brandWebsite)}
                  {...register('brandWebsite')}
                />
              </FormField>
            </div>

            <FormField
              label="What the business does"
              htmlFor="brandDescription"
              error={errors.brandDescription?.message}
              hint="At least 40 characters"
              required
            >
              <Textarea
                id="brandDescription"
                rows={4}
                placeholder="Small-batch speciality coffee roaster selling direct to consumers and to independent cafés, with a subscription tier."
                aria-invalid={Boolean(errors.brandDescription)}
                {...register('brandDescription')}
              />
            </FormField>

            <div className="grid gap-5 sm:grid-cols-2">
              <FormField label="Industry" htmlFor="industry" error={errors.industry?.message} required>
                <Select
                  value={industry}
                  onValueChange={(value) => {
                    setValue('industry', value as Industry, { shouldValidate: true })
                  }}
                >
                  <SelectTrigger id="industry" aria-invalid={Boolean(errors.industry)}>
                    <SelectValue placeholder="Choose one" />
                  </SelectTrigger>
                  <SelectContent>
                    {INDUSTRIES.map((value) => (
                      <SelectItem key={value} value={value}>
                        {value === 'saas' ? 'SaaS' : titleCase(value)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>

              <FormField
                label="Who you sell to"
                htmlFor="targetAudience"
                error={errors.targetAudience?.message}
                required
              >
                <Textarea
                  id="targetAudience"
                  rows={3}
                  placeholder="Urban home-brewing enthusiasts aged 25-40, plus independent café owners sourcing wholesale."
                  aria-invalid={Boolean(errors.targetAudience)}
                  {...register('targetAudience')}
                />
              </FormField>
            </div>
          </Card>
        </motion.div>

        {/* -------------------------------------------------- objectives */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...spring, delay: 0.05 }}
        >
          <Card className="space-y-5 p-6">
            <div>
              <h2 className="font-display text-base font-semibold">What you are trying to achieve</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                The Strategist weighs initiatives against these. Keep them concrete.
              </p>
            </div>

            <div className="space-y-3">
              {objectives.map((_, index) => (
                <div key={index} className="flex items-start gap-2">
                  <Input
                    placeholder={
                      index === 0 ? 'Grow direct subscription revenue' : 'Another objective'
                    }
                    aria-label={`Objective ${index + 1}`}
                    {...register(`objectives.${index}` as const)}
                  />
                  {objectives.length > 1 ? (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        setValue(
                          'objectives',
                          objectives.filter((_item, position) => position !== index),
                          { shouldValidate: true },
                        )
                      }}
                      aria-label={`Remove objective ${index + 1}`}
                    >
                      <Trash2 />
                    </Button>
                  ) : null}
                </div>
              ))}
              {errors.objectives ? (
                <p role="alert" className="text-xs text-destructive">
                  {errors.objectives.message ?? errors.objectives.root?.message}
                </p>
              ) : null}
            </div>

            {objectives.length < 6 ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setValue('objectives', [...objectives, ''])
                }}
              >
                <Plus />
                Add objective
              </Button>
            ) : null}
          </Card>
        </motion.div>

        {/* ------------------------------------------------- competitors */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...spring, delay: 0.1 }}
        >
          <Card className="space-y-5 p-6">
            <div>
              <h2 className="font-display text-base font-semibold">Competitors</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Who the Scout Agent goes and reads. One to five per run.
              </p>
            </div>

            <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-4">
              {competitors.fields.map((field, index) => (
                <motion.div
                  key={field.id}
                  variants={staggerItem}
                  className="rounded-lg border border-border/20 bg-muted/25 p-5"
                >
                  <div className="mb-4 flex items-center justify-between">
                    <p className="flex items-center gap-2 text-sm font-medium">
                      <Radar className="size-4 text-primary" />
                      Competitor {index + 1}
                    </p>
                    {competitors.fields.length > 1 ? (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => {
                          competitors.remove(index)
                        }}
                        aria-label={`Remove competitor ${index + 1}`}
                      >
                        <Trash2 />
                      </Button>
                    ) : null}
                  </div>

                  <div className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                      <FormField
                        label="Name"
                        htmlFor={`competitors.${index}.name`}
                        error={errors.competitors?.[index]?.name?.message}
                        required
                      >
                        <Input
                          id={`competitors.${index}.name`}
                          placeholder="Northbrew Coffee Co."
                          aria-invalid={Boolean(errors.competitors?.[index]?.name)}
                          {...register(`competitors.${index}.name` as const)}
                        />
                      </FormField>
                      <FormField
                        label="Landing page"
                        htmlFor={`competitors.${index}.landingPageUrl`}
                        error={errors.competitors?.[index]?.landingPageUrl?.message}
                        required
                      >
                        <Input
                          id={`competitors.${index}.landingPageUrl`}
                          placeholder="https://competitor.com"
                          aria-invalid={Boolean(errors.competitors?.[index]?.landingPageUrl)}
                          {...register(`competitors.${index}.landingPageUrl` as const)}
                        />
                      </FormField>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <FormField
                        label="Instagram"
                        htmlFor={`competitors.${index}.instagram`}
                        hint="Optional"
                      >
                        <Input
                          id={`competitors.${index}.instagram`}
                          placeholder="@handle"
                          {...register(`competitors.${index}.instagram` as const)}
                        />
                      </FormField>
                      <FormField
                        label="LinkedIn"
                        htmlFor={`competitors.${index}.linkedin`}
                        hint="Optional"
                      >
                        <Input
                          id={`competitors.${index}.linkedin`}
                          placeholder="company-slug"
                          {...register(`competitors.${index}.linkedin` as const)}
                        />
                      </FormField>
                    </div>

                    <FormField
                      label="Notes for the agents"
                      htmlFor={`competitors.${index}.notes`}
                      hint="Optional"
                    >
                      <Input
                        id={`competitors.${index}.notes`}
                        placeholder="Largest regional player. Heavy paid social spend."
                        {...register(`competitors.${index}.notes` as const)}
                      />
                    </FormField>
                  </div>
                </motion.div>
              ))}
            </motion.div>

            {errors.competitors?.root ? (
              <p role="alert" className="text-xs text-destructive">
                {errors.competitors.root.message}
              </p>
            ) : null}

            {competitors.fields.length < 5 ? (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  competitors.append({
                    name: '',
                    landingPageUrl: '',
                    instagram: '',
                    linkedin: '',
                    notes: '',
                  })
                }}
              >
                <Plus />
                Add competitor
              </Button>
            ) : null}
          </Card>
        </motion.div>

        <div className="flex flex-wrap items-center justify-end gap-3">
          <Button type="button" variant="ghost" onClick={() => { navigate('/app/projects') }}>
            Cancel
          </Button>
          <Button type="submit" size="lg" loading={createProject.isPending}>
            {createProject.isPending ? 'Creating…' : 'Create analysis'}
            {createProject.isPending ? null : <ArrowRight />}
          </Button>
        </div>
      </form>
    </div>
  )
}
