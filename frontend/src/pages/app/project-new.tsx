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
import { usePlatforms, useStartScrape } from '@/hooks/use-platforms'
import { MAX_SHORT_TEXT, newProjectSchema, type NewProjectValues } from '@/lib/validation'
import { titleCase } from '@/lib/utils'
import { spring, staggerContainer, staggerItem } from '@/lib/motion'
import { projectHomePath } from '@/lib/project-routes'
import type { ComparisonType, Industry, SocialComparisonPlatform } from '@/types/domain'

/**
 * What the user is comparing. Each option describes the *input* the user
 * supplies, because that is what changes on this form.
 *
 * All three have a real scraper behind them now, and all three scrape and
 * display rather than running the agent pipeline. The `available` flag stays
 * so a type can be switched off again in one line.
 */
const COMPARISON_TYPES: {
  value: ComparisonType
  label: string
  description: string
  available: boolean
}[] = [
  {
    value: 'website',
    label: 'Website',
    description: 'Compare landing pages and site content.',
    available: true,
  },
  {
    value: 'social_media',
    label: 'Social media platform',
    description: 'Compare social presence and recent posts.',
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

/** Stage 1: everything the Scout and Insight agents need before they start. */
export default function NewProjectPage() {
  useDocumentTitle('New analysis')
  const navigate = useNavigate()
  const createProject = useCreateProject()
  const startScrape = useStartScrape()

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
      competitors: [{ name: '', landingPageUrl: '', notes: '' }],
      comparisonType: 'ecommerce_product',
      ecommercePlatform: '',
      socialPlatform: '',
    },
  })

  const competitors = useFieldArray({ control, name: 'competitors' })
  const objectives = watch('objectives')
  const industry = watch('industry')
  const comparisonType = watch('comparisonType')
  const ecommercePlatform = watch('ecommercePlatform')
  const socialPlatform = watch('socialPlatform')

  // The platform list comes from the backend's scraper registry, so a newly
  // registered scraper appears here with no change to this file.
  const platforms = usePlatforms()
  const isEcommerce = comparisonType === 'ecommerce_product'
  const isSocial = comparisonType === 'social_media'
  const selectedPlatform = platforms.data?.find((item) => item.platform === ecommercePlatform)
  const selectedSocial = SOCIAL_PLATFORMS.find((item) => item.value === socialPlatform)

  const copy = FIELD_COPY[comparisonType]
  const ownUrlPlaceholder = isEcommerce
    ? (selectedPlatform?.urlExample ?? 'https://www.daraz.pk/products/...')
    : isSocial
      ? (selectedSocial?.example ?? 'https://www.instagram.com/yourpage')
      : 'https://yourbrand.com'
  const competitorUrlPlaceholder = isEcommerce
    ? (selectedPlatform?.urlExample ?? 'https://www.daraz.pk/products/...')
    : isSocial
      ? (selectedSocial?.example.replace('yourpage', 'competitor') ??
        'https://www.instagram.com/competitor')
      : 'https://competitor.com'

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
          Scraping starts as soon as you create the analysis. Both listings are read in the
          background, so you can leave the comparison page and come back.
        </p>
      </Card>

      <form onSubmit={onSubmit} className="space-y-6" noValidate>
        {/* --------------------------------------------- comparison type */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={spring}>
          <Card className="space-y-5 p-6">
            <div>
              <h2 className="font-display text-base font-semibold">What you are comparing</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Decides what the Scout Agent goes and reads. Everything after stage 2 is the same
                either way.
              </p>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
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
                  <SelectTrigger id="comparisonType" aria-invalid={Boolean(errors.comparisonType)}>
                    <SelectValue placeholder="Choose one" />
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

              {/* Only meaningful for an e-commerce comparison, so it appears
                  alongside rather than sitting disabled the rest of the time. */}
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
                    <SelectTrigger
                      id="ecommercePlatform"
                      aria-invalid={Boolean(errors.ecommercePlatform)}
                    >
                      <SelectValue
                        placeholder={platforms.isPending ? 'Loading…' : 'Choose a platform'}
                      />
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

              {/* Same placement and behaviour as the e-commerce platform. */}
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
                    <SelectTrigger id="socialPlatform" aria-invalid={Boolean(errors.socialPlatform)}>
                      <SelectValue placeholder="Choose a platform" />
                    </SelectTrigger>
                    <SelectContent>
                      {SOCIAL_PLATFORMS.map((item) => (
                        <SelectItem
                          key={item.value}
                          value={item.value}
                          disabled={!item.available}
                        >
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
            </div>

            {isSocial ? (
              <p className="text-sm text-muted-foreground">
                Both links must be pages on the selected platform.
              </p>
            ) : null}

            {isEcommerce ? (
              <p className="text-sm text-muted-foreground">
                Both links must be product pages on the selected platform. The Scout Agent reads
                each listing's price, specifications, images, reviews and seller details, then
                compares them field by field.
              </p>
            ) : null}
          </Card>
        </motion.div>

        {/* ------------------------------------------------------- brand */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...spring, delay: 0.05 }}
        >
          <Card className="space-y-5 p-6">
            <div>
              <h2 className="font-display text-base font-semibold">Your brand</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                The subject of the analysis: the business the gaps will be measured against.
              </p>
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <FormField
                label={copy.nameLabel}
                htmlFor="brandName"
                error={errors.brandName?.message}
                required
              >
                <Input
                  id="brandName"
                  placeholder={copy.namePlaceholder}
                  aria-invalid={Boolean(errors.brandName)}
                  {...register('brandName')}
                />
              </FormField>

              {/* One field, relabelled per type: the user's website, social
                  page or product listing. Required on all three, because it is
                  the baseline every comparison is measured against. */}
              <FormField
                label={copy.ownUrlLabel}
                htmlFor="brandWebsite"
                error={errors.brandWebsite?.message}
                required
              >
                <Input
                  id="brandWebsite"
                  placeholder={ownUrlPlaceholder}
                  aria-invalid={Boolean(errors.brandWebsite)}
                  {...register('brandWebsite')}
                />
              </FormField>
            </div>

            <FormField
              label="What the business does"
              htmlFor="brandDescription"
              error={errors.brandDescription?.message}
              hint={`Up to ${MAX_SHORT_TEXT} characters`}
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
                hint={`Optional, up to ${MAX_SHORT_TEXT} characters`}
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
          transition={{ ...spring, delay: 0.1 }}
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
          transition={{ ...spring, delay: 0.15 }}
        >
          <Card className="space-y-5 p-6">
            <div>
              <h2 className="font-display text-base font-semibold">Competitors</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {isEcommerce
                  ? 'The listings to measure yours against. One to five per run.'
                  : 'Who the Scout Agent goes and reads. One to five per run.'}
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
