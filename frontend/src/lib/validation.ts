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

const urlSchema = z
  .string()
  .url('Enter a full URL, including https://')
  .max(500, 'That URL is too long')

export const competitorSchema = z.object({
  name: z.string().min(2, 'Enter the competitor name').max(120),
  landingPageUrl: urlSchema,
  instagram: z.string().max(60).optional().or(z.literal('')),
  linkedin: z.string().max(60).optional().or(z.literal('')),
  notes: z.string().max(500).optional().or(z.literal('')),
})

export const newProjectSchema = z.object({
  brandName: z.string().min(2, 'Enter your brand name').max(120),
  brandWebsite: urlSchema.optional().or(z.literal('')),
  brandDescription: z
    .string()
    .min(40, 'Describe the business in at least 40 characters, the agents rely on this')
    .max(1200),
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
    .min(20, 'Describe who you sell to in at least 20 characters')
    .max(600),
  objectives: z
    .array(z.string().min(3).max(160))
    .min(1, 'Add at least one objective')
    .max(6, 'Six objectives is plenty, keep the run focused'),
  competitors: z
    .array(competitorSchema)
    .min(1, 'Add at least one competitor to analyse')
    .max(5, 'Five competitors is the current per-run limit'),
})
export type NewProjectValues = z.infer<typeof newProjectSchema>

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
