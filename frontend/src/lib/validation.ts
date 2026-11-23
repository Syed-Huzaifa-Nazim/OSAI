import { z } from 'zod'

/**
 * Shared schemas. The same rules run client-side (react-hook-form + zod) and
 * are mirrored by the Pydantic models on the backend, a client that skips
 * validation still cannot write a bad row.
 */

export const emailSchema = z
  .string()
  .min(1, 'Enter your email address')
  .email('That does not look like a valid email address')

export const passwordSchema = z
  .string()
  .min(8, 'Use at least 8 characters')
  .max(72, 'Passwords cannot be longer than 72 characters')
  .regex(/[a-z]/, 'Include at least one lowercase letter')
  .regex(/[A-Z]/, 'Include at least one uppercase letter')
  .regex(/[0-9]/, 'Include at least one number')

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Enter your password'),
})
export type LoginValues = z.infer<typeof loginSchema>

export const signupSchema = z
  .object({
    fullName: z.string().min(2, 'Enter your name').max(80, 'That name is too long'),
    email: emailSchema,
    password: passwordSchema,
    confirmPassword: z.string().min(1, 'Confirm your password'),
    acceptTerms: z.literal(true, {
      errorMap: () => ({ message: 'You need to accept the terms to continue' }),
    }),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: 'Those passwords do not match',
    path: ['confirmPassword'],
  })
export type SignupValues = z.infer<typeof signupSchema>

export const forgotPasswordSchema = z.object({ email: emailSchema })
export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>

export const resetPasswordSchema = z
  .object({
    password: passwordSchema,
    confirmPassword: z.string().min(1, 'Confirm your password'),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: 'Those passwords do not match',
    path: ['confirmPassword'],
  })
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>

export const contactSchema = z.object({
  name: z.string().min(2, 'Enter your name').max(80),
  email: emailSchema,
  organisation: z.string().max(120).optional().or(z.literal('')),
  message: z
    .string()
    .min(20, 'Tell us a little more, at least 20 characters')
    .max(2000, 'Please keep it under 2000 characters'),
})
export type ContactValues = z.infer<typeof contactSchema>

/**
 * Upper bound on any link.
 *
 * Marketplace links copied out of search results carry kilobytes of tracking
 * parameters -- a real Daraz product link runs past 1,100 characters -- so the
 * old 500-character cap rejected ordinary input with "That URL is too long".
 * 8,192 matches the backend (MAX_URL_LENGTH in app/models/project.py): the
 * request-line limit most web servers enforce, so no link a site can actually
 * serve is longer.
 */
export const MAX_URL_LENGTH = 8192

/** Shared cap for the two short free-text intake fields. Mirrors the backend. */
export const MAX_SHORT_TEXT = 120
/** What the business does: room for products, ordering terms and address. */
export const MAX_DESCRIPTION = 500

const urlSchema = z
  .string()
  .trim()
  .min(1, 'Add a link here')
  .url('Enter a full URL, including https://')
  .max(MAX_URL_LENGTH, 'That link is longer than any site can serve')

export const competitorSchema = z.object({
  name: z.string().min(2, 'Enter the competitor name').max(120),
  landingPageUrl: urlSchema,
  notes: z.string().max(500).optional().or(z.literal('')),
})

/**
 * Which host a link must belong to, per platform.
 *
 * Covers the e-commerce platforms (mirroring the backend scrapers' link checks,
 * ALLOWED_HOST_FRAGMENTS in app/scrapers/daraz/selectors.py and
 * PRODUCT_URL_PATTERNS in app/scrapers/alibaba/selectors.py) and the social
 * ones (mirroring SOCIAL_PLATFORM_HOSTS in app/models/project.py), so a wrong
 * link is caught on the form rather than after a pipeline run starts.
 *
 * `productId`, where a platform has one, reads the listing's id out of a link,
 * so the same product under two differently worded links is still recognised
 * as one listing.
 *
 * Keyed by platform so a new one adds an entry rather than an if-branch. A
 * platform with no entry is accepted as any valid URL and left for the backend
 * to judge.
 */
const PLATFORM_URL_RULES: Record<
  string,
  { pattern: RegExp; message: string; productId?: (url: URL) => string | null }
> = {
  daraz: {
    pattern: /^https?:\/\/([a-z0-9-]+\.)*daraz\.[a-z.]+\//i,
    message: 'Enter a Daraz product link, e.g. https://www.daraz.pk/products/...',
  },
  alibaba: {
    // alibaba.com or a subdomain (www., m., french.), on a single product page:
    // desktop /product-detail/<Title>_<id>.html or mobile /product/<id>[/<Title>].
    pattern:
      /^https?:\/\/([a-z0-9-]+\.)*alibaba\.com\/(product-detail\/[^/?#]*_\d{6,}\.html|product\/\d{6,}(\/[^/?#]+)?(\.html)?\/?)(?=[?#]|$)/i,
    message: 'Enter an Alibaba product link, e.g. https://www.alibaba.com/product-detail/...',
    productId: (url) =>
      /^\/product-detail\/[^/]*_(\d{6,})\.html$/i.exec(url.pathname)?.[1] ??
      /^\/product\/(\d{6,})/i.exec(url.pathname)?.[1] ??
      null,
  },
  facebook: {
    // The host itself or a subdomain (m., web.), never a lookalike such as
    // facebook.com.example.net: the host has to end right there.
    pattern: /^https?:\/\/([a-z0-9-]+\.)*(facebook\.com|fb\.com)(?=[/?#:]|$)/i,
    message: 'Enter a Facebook link, e.g. https://www.facebook.com/yourpage',
  },
  instagram: {
    pattern: /^https?:\/\/([a-z0-9-]+\.)*instagram\.com(?=[/?#:]|$)/i,
    message: 'Enter an Instagram link, e.g. https://www.instagram.com/yourpage',
  },
}

export function isValidPlatformUrl(platform: string, url: string): boolean {
  const rule = PLATFORM_URL_RULES[platform]
  if (!rule) return true
  return rule.pattern.test(url.trim())
}

export function platformUrlMessage(platform: string): string {
  return PLATFORM_URL_RULES[platform]?.message ?? 'Enter a full URL, including https://'
}

export const newProjectSchema = z
  .object({
    brandName: z.string().trim().min(2, 'Enter a name').max(120),
    /** The user's own link. Required on every comparison type; what it has to
     *  point at depends on the type, checked below. */
    brandWebsite: urlSchema,
    brandDescription: z
      .string()
      .trim()
      .min(1, 'Describe what the business does')
      .max(MAX_DESCRIPTION, `Keep this to ${MAX_DESCRIPTION} characters or fewer`),
    industry: z.enum([
      'saas',
      'ecommerce',
      'fintech',
      'healthcare',
      'education',
      'hospitality',
      'agency',
      'manufacturing',
      'other',
    ]),
    targetAudience: z
      .string()
      .trim()
      .max(MAX_SHORT_TEXT, `Keep this to ${MAX_SHORT_TEXT} characters or fewer`)
      .optional(),
    objectives: z
      .array(z.string().min(3).max(160))
      .min(1, 'Add at least one objective')
      .max(6, 'Six objectives is plenty, keep the run focused'),
    competitors: z
      .array(competitorSchema)
      .min(1, 'Add at least one competitor to analyse')
      .max(1, 'One competitor per analysis'),
    comparisonType: z.enum(['website', 'social_media', 'ecommerce_product']),
    ecommercePlatform: z.string().max(40).optional().or(z.literal('')),
    socialPlatform: z.enum(['facebook', 'instagram']).optional().or(z.literal('')),
  })
  /**
   * Rules that depend on what is being compared.
   *
   * Social and e-commerce comparisons need a platform, and both the user's
   * link and every competitor's have to live on it. A website comparison has
   * no platform. These are in a superRefine because each depends on another
   * field's value.
   *
   * Mirrored by ProjectCreate.check_type_specific_inputs on the backend, so a
   * client that skips validation still cannot create a bad project.
   */
  .superRefine((values, ctx) => {
    if (values.comparisonType === 'website') return

    const isSocial = values.comparisonType === 'social_media'
    const platform = (isSocial ? values.socialPlatform : values.ecommercePlatform) ?? ''
    const platformField = isSocial ? 'socialPlatform' : 'ecommercePlatform'

    if (!platform) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: [platformField],
        message: isSocial ? 'Choose a social media platform' : 'Choose an e-commerce platform',
      })
      return
    }

    // Facebook is listed so the plan is visible, but nothing can read it yet.
    // Mirrors the same refusal in ProjectCreate._check_social on the backend.
    if (isSocial && platform === 'facebook') {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['socialPlatform'],
        message: 'Facebook comparisons are not available yet. Choose Instagram.',
      })
      return
    }

    // An empty or malformed link already has its own field error; only judge
    // the host of a link that is otherwise valid.
    const ownUrl = values.brandWebsite
    if (ownUrl && !isValidPlatformUrl(platform, ownUrl)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ['brandWebsite'],
        message: platformUrlMessage(platform),
      })
    }

    values.competitors.forEach((competitor, index) => {
      const url = competitor.landingPageUrl
      if (!url) return
      if (!isValidPlatformUrl(platform, url)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['competitors', index, 'landingPageUrl'],
          message: platformUrlMessage(platform),
        })
      } else if (!isSocial && ownUrl && listingKey(platform, url) === listingKey(platform, ownUrl)) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          path: ['competitors', index, 'landingPageUrl'],
          message: 'This is the same listing as yours, use a different product',
        })
      }
    })
  })
export type NewProjectValues = z.infer<typeof newProjectSchema>

/**
 * One key per marketplace listing, for spotting the same listing on both sides.
 *
 * Two copies of the same listing carry different tracking parameters
 * depending on where they were copied from, so comparing raw strings would
 * miss a duplicate. Where the platform puts a product id in its links, the id
 * alone decides (a desktop link, a mobile link and a reworded title are one
 * product); otherwise the host and path do. The backend does the same thing
 * properly, per platform.
 */
function listingKey(platform: string, url: string): string {
  try {
    const parsed = new URL(url)
    const productId = PLATFORM_URL_RULES[platform]?.productId?.(parsed)
    if (productId) return `${platform}:${productId}`
    return `${parsed.hostname.replace(/^www\./, '')}${parsed.pathname}`.toLowerCase()
  } catch {
    return url.trim().toLowerCase()
  }
}

export const profileSchema = z.object({
  fullName: z.string().min(2, 'Enter your name').max(80),
})
export type ProfileValues = z.infer<typeof profileSchema>

export const changePasswordSchema = z
  .object({
    password: passwordSchema,
    confirmPassword: z.string().min(1, 'Confirm your new password'),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: 'Those passwords do not match',
    path: ['confirmPassword'],
  })
export type ChangePasswordValues = z.infer<typeof changePasswordSchema>
