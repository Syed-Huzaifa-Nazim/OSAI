import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFieldArray, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  Building2,
  ChevronRight,
  Goal,
  Info,
  Lightbulb,
  Plus,
  Scale,
  Trash2,
  Trophy,
} from 'lucide-react'
import { CompareAnimation } from '@/components/shared/compare-animation'
import { SectionHead } from '@/components/shared/section-head'
import { USER_STEPS } from '@/lib/user-steps'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
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
import { useCreateProject } from '@/hooks/use-projects'
import { useDocumentTitle } from '@/hooks/use-document-title'
import { usePlatforms, useStartScrape } from '@/hooks/use-platforms'
import { MAX_DESCRIPTION, MAX_SHORT_TEXT, newProjectSchema, type NewProjectValues } from '@/lib/validation'
import { titleCase } from '@/lib/utils'
import { spring, staggerContainer, staggerItem } from '@/lib/motion'
import { projectHomePath } from '@/lib/project-routes'
import type { ComparisonType, Industry, SocialComparisonPlatform } from '@/types/domain'

/**
 * What the user is comparing. Each option describes the *input* the user
 * supplies, because that is what changes on this form.
 *
 * Instagram and marketplace listings are offered. Website comparison was dropped from the UI (no time and no
 * data to build its gap analysis); its code stays so older website projects still open.
 */
const COMPARISON_TYPES: {
  value: ComparisonType
  label: string
  description: string
  available: boolean
}[] = [
  {
    value: 'social_media',
    label: 'Instagram or other social media',
    description: 'Compare two accounts and their recent posts.',
    available: true,
  },
  {
    value: 'ecommerce_product',
    label: 'E-commerce product',
    description: 'Compare two marketplace product listings, field by field.',
    available: true,
  },
]

/**
 * The social platforms a social-media comparison can run against. Static,
 * unlike the e-commerce list: there is no social scraper registry to serve it.
 * Keep in step with SocialComparisonPlatform in backend/app/models/project.py.
 *
 * Only Instagram can be read today. Facebook stays listed, and disabled, so the
 * plan is visible without letting anyone start a comparison nothing can scrape.
 * The backend refuses it too, so this is a courtesy, not the enforcement.
 */
const SOCIAL_PLATFORMS: {
  value: SocialComparisonPlatform
  label: string
  example: string
  available: boolean
}[] = [
  {
    value: 'facebook',
    label: 'Facebook',
    example: 'https://www.facebook.com/yourpage',
    available: false,
  },
  {
    value: 'instagram',
    label: 'Instagram',
    example: 'https://www.instagram.com/yourpage',
    available: true,
  },
]

/**
 * What each comparison type calls the fields it shares. The underlying form
 * fields are the same three -- a name, the user's own link, a competitor link --
 * so they are relabelled per type instead of being duplicated.
 */
const FIELD_COPY: Record<
  ComparisonType,
  {
    nameLabel: string
    namePlaceholder: string
    ownUrlLabel: string
    competitorUrlLabel: string
  }
> = {
  website: {
    nameLabel: 'Brand name',
    namePlaceholder: 'Verdant Roast',
    ownUrlLabel: 'Website',
    competitorUrlLabel: 'Landing page',
  },
  social_media: {
    nameLabel: 'Page name',
    namePlaceholder: 'Verdant Roast Coffee',
    ownUrlLabel: 'Platform link',
    competitorUrlLabel: "Competitor's Platform link",
  },
  ecommerce_product: {
    nameLabel: 'Product name',
    namePlaceholder: 'Stainless steel electric kettle 1.7L',
    ownUrlLabel: 'Your product link',
    competitorUrlLabel: 'Product link',
  },
}

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

/** Each platform's logo, shown inside the platform choice. */
const PLATFORM_LOGO: Record<string, string> = {
  instagram: '/hero/instagram.png',
  facebook: '/hero/facebook.png',
  daraz: '/hero/daraz-mark.png',
  alibaba: '/hero/alibaba-mark.png',
}

/** The fields on page 1; Next checks only these before moving on. */
const PAGE_ONE_FIELDS = [
  'comparisonType',
  'ecommercePlatform',
  'socialPlatform',
  'brandName',
  'brandWebsite',
  'brandDescription',
] as const

const CARD = 'rounded-[1.75rem] border border-border/15 bg-card/95 p-6 shadow-[0_24px_60px_-32px_hsl(var(--shadow-color)/0.45)] sm:p-7'

/** The six steps, step 1 current: the same steps every page shows. */
function StepsBar() {
  return (
    <ol className="flex min-w-[34rem] items-start" aria-label="The six steps of an analysis">
      {USER_STEPS.map((step, index) => (
        <li key={step.label} className="flex flex-1 flex-col items-center gap-1.5 text-center text-xs leading-tight text-muted-foreground">
          <span className="relative flex w-full justify-center">
            {index > 0 ? (
              <span
                className={cn(
                  'absolute right-1/2 top-1/2 mr-5 h-0.5 w-[calc(100%-2.5rem)] rounded-full',
                  index === 1 ? 'bg-gradient-to-r from-primary to-border/40' : 'bg-border/40',
                )}
                aria-hidden="true"
              />
            ) : null}
            <span
              className={cn(
                'relative flex size-10 items-center justify-center rounded-full text-sm font-bold',
                index === 0
                  ? 'bg-primary text-primary-foreground shadow-[0_0_0_6px_hsl(var(--primary)/0.15)]'
                  : 'border border-border/40 bg-card text-primary',
              )}
            >
              {index + 1}
            </span>
          </span>
          <span className={cn('max-w-[6.5rem]', index === 0 && 'font-semibold text-foreground')}>{step.label}</span>
          {!step.built ? <span className="-mt-1 text-[10px] font-semibold">Soon</span> : step.you ? <span className="-mt-1 text-[10px] font-semibold text-warning-ink">You</span> : null}
        </li>
      ))}
    </ol>
  )
}

export default function NewProjectPage() {
  useDocumentTitle('New analysis')
  const navigate = useNavigate()
  const createProject = useCreateProject()
  const startScrape = useStartScrape()
  const [page, setPage] = useState<1 | 2>(1)

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    trigger,
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
      competitors: [{ name: '', landingPageUrl: '', notes: '' }],
      comparisonType: 'social_media',
      ecommercePlatform: '',
      socialPlatform: 'instagram',
    },
  })

  const competitors = useFieldArray({ control, name: 'competitors' })
  const objectives = watch('objectives')
  const industry = watch('industry')
  const comparisonType = watch('comparisonType')
  const ecommercePlatform = watch('ecommercePlatform')
  const socialPlatform = watch('socialPlatform')
  const descriptionLength = (watch('brandDescription') ?? '').length

  // The platform list comes from the backend's scraper registry, so a newly
  // registered scraper appears here with no change to this file.
  const platforms = usePlatforms()
  const isEcommerce = comparisonType === 'ecommerce_product'
  const isSocial = comparisonType === 'social_media'
  const selectedPlatform = platforms.data?.find((item) => item.platform === ecommercePlatform)
  const selectedSocial = SOCIAL_PLATFORMS.find((item) => item.value === socialPlatform)
  const platformLogo = PLATFORM_LOGO[(isSocial ? socialPlatform : ecommercePlatform) ?? '']

  const copy = FIELD_COPY[comparisonType]
  const ownUrlPlaceholder = isEcommerce
    ? (selectedPlatform?.urlExample ?? 'https://www.daraz.pk/products/...')
    : (selectedSocial?.example ?? 'https://www.instagram.com/yourpage')
  const competitorUrlPlaceholder = isEcommerce
    ? (selectedPlatform?.urlExample ?? 'https://www.daraz.pk/products/...')
    : (selectedSocial?.example.replace('yourpage', 'competitor') ?? 'https://www.instagram.com/competitor')

  const goNext = async () => {
    if (await trigger([...PAGE_ONE_FIELDS])) {
      setPage(2)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  const onSubmit = handleSubmit((values) => {
    createProject.mutate(
      {
        brandName: values.brandName,
        brandWebsite: values.brandWebsite,
        brandDescription: values.brandDescription,
        industry: values.industry,
        targetAudience: values.targetAudience || null,
        objectives: values.objectives.filter((objective) => objective.trim().length > 0),
        comparisonType: values.comparisonType,
        ecommercePlatform:
          values.comparisonType === 'ecommerce_product'
            ? (values.ecommercePlatform || null)
            : null,
        socialPlatform:
          values.comparisonType === 'social_media' ? (values.socialPlatform || null) : null,
        competitors: values.competitors.map((competitor) => ({
          name: competitor.name,
          landingPageUrl: competitor.landingPageUrl,
          // No longer collected on any comparison type.
          socialHandles: [],
          notes: competitor.notes || null,
        })),
      },
      {
        onSuccess: (project) => {
          // Scraping starts straight away, whatever is being compared. The page
          // the project opens on follows its progress, and offers a retry if
          // this call itself fails.
          startScrape.mutate(project.id)
          navigate(projectHomePath(project))
        },
      },
    )
  })

  /** The note and the buttons; on page 2 they sit right under the competitor card (no empty gap). */
  const footer = (stacked: boolean) => (
    <div className={cn('flex flex-col-reverse items-stretch gap-4', !stacked && 'sm:flex-row sm:items-center sm:justify-between')}>
      <p className="inline-flex items-center gap-2 self-start rounded-full bg-primary/5 px-4 py-2 text-sm text-muted-foreground">
        <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
          <Info className="size-3" aria-hidden="true" />
        </span>
        Page {page} of 2 · Reading starts as soon as you create the analysis.
      </p>
      <div className="flex items-center justify-end gap-3">
        <Button
          type="button"
          variant="ghost"
          className="text-primary"
          onClick={() => {
            if (page === 2) {
              setPage(1)
              window.scrollTo({ top: 0, behavior: 'smooth' })
            } else {
              navigate('/app/projects')
            }
          }}
        >
          {page === 2 ? (
            <>
              <ArrowLeft /> Back
            </>
          ) : (
            'Cancel'
          )}
        </Button>
        <Button
          type="submit"
          size="lg"
          loading={page === 2 && createProject.isPending}
          className="h-14 rounded-full border-4 border-card bg-warning px-9 text-base text-warning-foreground shadow-[0_14px_30px_-10px_hsl(var(--warning)/0.75)] hover:bg-warning/90"
        >
          {page === 1 ? 'Next' : createProject.isPending ? 'Creating…' : 'Create analysis'}
          {page === 2 && createProject.isPending ? null : <ArrowRight />}
        </Button>
      </div>
    </div>
  )

  return (
    <div className="relative mx-auto max-w-6xl space-y-7 pb-4">
      {/* ---------------------------------------------------- title + steps */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={spring}
        className="grid items-center gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.25fr)]"
      >
        <div className="border-l-4 border-warning pl-5">
          <h1 className="font-display text-2xl font-extrabold leading-tight sm:text-3xl">
            Let&rsquo;s uncover what&rsquo;s working for your competitor
          </h1>
          <p className="mt-1.5 text-sm text-muted-foreground sm:text-base">
            Answer a few simple questions to start your analysis.
          </p>
        </div>
        <div className="-mx-1 overflow-x-auto px-1 pb-1">
          <StepsBar />
        </div>
      </motion.div>

      <form
        onSubmit={(event) => {
          if (page === 1) {
            event.preventDefault()
            void goNext()
            return
          }
          void onSubmit(event)
        }}
        className="space-y-6"
        noValidate
      >
        {/* =============================================== page 1 */}
        <div className={cn(page === 1 ? 'block' : 'hidden')}>
          <div className="grid items-center gap-6 lg:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] xl:grid-cols-[minmax(0,0.75fr)_minmax(0,1fr)_auto_minmax(0,1fr)]">
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={spring}
              className="hidden xl:block"
            >
              <CompareAnimation />
            </motion.div>

            {/* ------------------------------ analysis details */}
            <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ ...spring, delay: 0.05 }} className={cn(CARD, 'h-full space-y-5')}>
              <SectionHead icon={BarChart3} title="Analysis details" subtitle="Tell us what you want to compare." />

              <FormField
                label="Comparison type"
                htmlFor="comparisonType"
                error={errors.comparisonType?.message}
                hint={COMPARISON_TYPES.find((item) => item.value === comparisonType)?.description}
                required
              >
                <Select
                  value={comparisonType}
                  onValueChange={(value) => {
                    setValue('comparisonType', value as ComparisonType, { shouldValidate: true })
                    // Clearing a platform when leaving its type keeps a stale
                    // choice from being submitted on a different project.
                    if (value !== 'ecommerce_product') {
                      setValue('ecommercePlatform', '', { shouldValidate: true })
                    }
                    if (value !== 'social_media') {
                      setValue('socialPlatform', '', { shouldValidate: true })
                    }
                  }}
                >
                  <SelectTrigger id="comparisonType" className="h-12" aria-invalid={Boolean(errors.comparisonType)}>
                    <div className="flex min-w-0 items-center gap-3">
                      <Scale className="size-5 text-primary" aria-hidden="true" />
                      <SelectValue placeholder="Choose one" />
                    </div>
                  </SelectTrigger>
                  <SelectContent>
                    {COMPARISON_TYPES.map((item) => (
                      <SelectItem key={item.value} value={item.value} disabled={!item.available}>
                        {item.label}
                        {item.available ? null : (
                          <span className="ml-2 text-xs text-muted-foreground">Coming soon</span>
                        )}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>

              {/* Only meaningful for an e-commerce comparison. */}
              {isEcommerce ? (
                <FormField
                  label="Platform"
                  htmlFor="ecommercePlatform"
                  error={errors.ecommercePlatform?.message}
                  hint={selectedPlatform?.urlHint ?? 'Where both listings are hosted'}
                  required
                >
                  <Select
                    value={ecommercePlatform || undefined}
                    onValueChange={(value) => {
                      setValue('ecommercePlatform', value, { shouldValidate: true })
                    }}
                    disabled={platforms.isPending}
                  >
                    <SelectTrigger id="ecommercePlatform" className="h-12" aria-invalid={Boolean(errors.ecommercePlatform)}>
                      <div className="flex min-w-0 items-center gap-3">
                        {platformLogo ? <img src={platformLogo} alt="" className="size-6 rounded-md object-contain" /> : null}
                        <SelectValue placeholder={platforms.isPending ? 'Loading…' : 'Choose a platform'} />
                      </div>
                    </SelectTrigger>
                    <SelectContent>
                      {(platforms.data ?? []).map((item) => (
                        <SelectItem key={item.platform} value={item.platform}>
                          {item.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
              ) : null}

              {isSocial ? (
                <FormField
                  label="Platform"
                  htmlFor="socialPlatform"
                  error={errors.socialPlatform?.message}
                  hint="Where both pages are hosted"
                  required
                >
                  <Select
                    value={socialPlatform || undefined}
                    onValueChange={(value) => {
                      setValue('socialPlatform', value as SocialComparisonPlatform, {
                        shouldValidate: true,
                      })
                    }}
                  >
                    <SelectTrigger id="socialPlatform" className="h-12" aria-invalid={Boolean(errors.socialPlatform)}>
                      <div className="flex min-w-0 items-center gap-3">
                        {platformLogo ? <img src={platformLogo} alt="" className="size-6 rounded-md object-contain" /> : null}
                        <SelectValue placeholder="Choose a platform" />
                      </div>
                    </SelectTrigger>
                    <SelectContent>
                      {SOCIAL_PLATFORMS.map((item) => (
                        <SelectItem key={item.value} value={item.value} disabled={!item.available}>
                          {item.label}
                          {item.available ? null : (
                            <span className="ml-2 text-xs text-muted-foreground">Coming soon</span>
                          )}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </FormField>
              ) : null}

              <div className="flex gap-3 rounded-2xl bg-primary/5 p-4">
                <Lightbulb className="size-7 shrink-0 fill-warning text-warning-ink" aria-hidden="true" />
                <p className="text-sm text-primary">
                  {isEcommerce
                    ? 'We read both listings (price, specifications, images, reviews and seller details) and compare them field by field. Both links must be product pages on this platform.'
                    : 'We read the latest posts of both pages, find what works for your competitor that you are not doing yet, and show the real posts behind each gap. Both links must be on this platform.'}
                </p>
              </div>
            </motion.div>

            <motion.button
              type="button"
              onClick={() => {
                void goNext()
              }}
              whileHover={{ x: 3 }}
              className="hidden size-12 items-center justify-center self-center rounded-full border border-primary/25 bg-card text-primary shadow-md lg:flex"
              aria-label="Next page"
            >
              <ChevronRight className="size-5" />
            </motion.button>

            {/* ------------------------------------ your brand */}
            <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ ...spring, delay: 0.1 }} className={cn(CARD, 'h-full space-y-5')}>
              <SectionHead icon={Building2} title="Your brand" subtitle="Tell us about your brand: the gaps are measured against it." />

              <FormField label={copy.nameLabel} htmlFor="brandName" error={errors.brandName?.message} required>
                <Input
                  id="brandName"
                  className="h-12"
                  placeholder={`e.g. ${copy.namePlaceholder}`}
                  aria-invalid={Boolean(errors.brandName)}
                  {...register('brandName')}
                />
              </FormField>

              {/* One field, relabelled per type: the user's social page or product listing. */}
              <FormField label={copy.ownUrlLabel} htmlFor="brandWebsite" error={errors.brandWebsite?.message} required>
                <Input
                  id="brandWebsite"
                  className="h-12"
                  placeholder={ownUrlPlaceholder}
                  aria-invalid={Boolean(errors.brandWebsite)}
                  {...register('brandWebsite')}
                />
              </FormField>

              <FormField
                label="What the business does"
                htmlFor="brandDescription"
                error={errors.brandDescription?.message}
                hint={`Up to ${MAX_DESCRIPTION} characters`}
                required
              >
                <div className="relative">
                  <Textarea
                    id="brandDescription"
                    rows={5}
                    placeholder="e.g. Small-batch coffee roaster selling direct to consumers and independent cafés."
                    aria-invalid={Boolean(errors.brandDescription)}
                    {...register('brandDescription')}
                  />
                  <span
                    className={cn(
                      'pointer-events-none absolute bottom-2 right-3 text-[11px] tabular-nums',
                      descriptionLength > MAX_DESCRIPTION ? 'text-destructive' : 'text-muted-foreground',
                    )}
                  >
                    {descriptionLength}/{MAX_DESCRIPTION}
                  </span>
                </div>
              </FormField>
            </motion.div>
          </div>
        </div>

        {/* =============================================== page 2 */}
        <div className={cn(page === 2 ? 'block' : 'hidden')}>
          <div className="grid items-start gap-6 lg:grid-cols-2">
            {/* ----------------------------- goals and audience */}
            <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={spring} className={cn(CARD, 'space-y-5')}>
              <SectionHead icon={Goal} title="Your goals" subtitle="What you sell, to whom, and what you want to achieve." />

              <FormField label="Industry" htmlFor="industry" error={errors.industry?.message} required>
                <Select
                  value={industry}
                  onValueChange={(value) => {
                    setValue('industry', value as Industry, { shouldValidate: true })
                  }}
                >
                  <SelectTrigger id="industry" className="h-12" aria-invalid={Boolean(errors.industry)}>
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
                hint={`Optional, up to ${MAX_SHORT_TEXT} characters`}
              >
                <Textarea
                  id="targetAudience"
                  rows={2}
                  placeholder="e.g. Home-brewing enthusiasts aged 25-40, and café owners buying wholesale."
                  aria-invalid={Boolean(errors.targetAudience)}
                  {...register('targetAudience')}
                />
              </FormField>

              <div className="space-y-2">
                <p className="text-sm font-medium">What you are trying to achieve</p>
                {objectives.map((_, index) => (
                  <div key={index} className="flex items-start gap-2">
                    <Input
                      className="h-11"
                      placeholder={index === 0 ? 'e.g. Grow direct subscription revenue' : 'Another goal'}
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
              </div>
            </motion.div>

            {/* ------------------------------------ competitor + buttons */}
            <div className="space-y-5">
            <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ ...spring, delay: 0.05 }} className={cn(CARD, 'space-y-5')}>
              <SectionHead
                icon={Trophy}
                tone="warning"
                title="Your competitor"
                subtitle={
                  isEcommerce
                    ? 'The listing to measure yours against.'
                    : 'The page the Scout Engine reads and compares with yours.'
                }
              />

              <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-4">
                {competitors.fields.map((field, index) => (
                  <motion.div key={field.id} variants={staggerItem} className="rounded-2xl border border-border/15 bg-muted/30 p-4">
                    <div className="space-y-3">
                      <FormField
                        label="Name"
                        htmlFor={`competitors.${index}.name`}
                        error={errors.competitors?.[index]?.name?.message}
                        required
                      >
                        <Input
                          id={`competitors.${index}.name`}
                          placeholder="e.g. Northbrew Coffee Co."
                          aria-invalid={Boolean(errors.competitors?.[index]?.name)}
                          {...register(`competitors.${index}.name` as const)}
                        />
                      </FormField>
                      <FormField
                        label={copy.competitorUrlLabel}
                        htmlFor={`competitors.${index}.landingPageUrl`}
                        error={errors.competitors?.[index]?.landingPageUrl?.message}
                        required
                      >
                        <Input
                          id={`competitors.${index}.landingPageUrl`}
                          placeholder={competitorUrlPlaceholder}
                          aria-invalid={Boolean(errors.competitors?.[index]?.landingPageUrl)}
                          {...register(`competitors.${index}.landingPageUrl` as const)}
                        />
                      </FormField>
                      <FormField label="Notes" htmlFor={`competitors.${index}.notes`} hint="Optional">
                        <Input
                          id={`competitors.${index}.notes`}
                          placeholder="e.g. Largest regional player."
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
            </motion.div>
            {page === 2 ? footer(true) : null}
            </div>
          </div>
        </div>

        {page === 1 ? footer(false) : null}
      </form>
    </div>
  )
}
