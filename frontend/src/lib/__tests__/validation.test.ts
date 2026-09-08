import { describe, expect, it } from 'vitest'
import {
  loginSchema,
  newProjectSchema,
  passwordSchema,
  signupSchema,
} from '@/lib/validation'

const VALID_PROJECT = {
  brandName: 'Verdant Roast',
  brandWebsite: 'https://verdantroast.example',
  brandDescription:
    'Small-batch speciality coffee roaster selling direct to consumers and to independent cafes.',
  industry: 'ecommerce' as const,
  targetAudience: 'Urban home-brewing enthusiasts aged 25-40 who buy whole bean monthly.',
  objectives: ['Grow direct subscription revenue'],
  competitors: [
    {
      name: 'Northbrew Coffee Co.',
      landingPageUrl: 'https://northbrew.example',
      instagram: '@northbrewco',
      linkedin: '',
      notes: '',
    },
  ],
}

describe('passwordSchema', () => {
  it('accepts a password meeting every rule', () => {
    expect(passwordSchema.safeParse('Str0ngPass').success).toBe(true)
  })

  it.each([
    ['Sh0rt', 'too short'],
    ['alllowercase1', 'no uppercase'],
    ['ALLUPPERCASE1', 'no lowercase'],
    ['NoDigitsHere', 'no number'],
  ])('rejects %s (%s)', (password) => {
    expect(passwordSchema.safeParse(password).success).toBe(false)
  })
})

describe('signupSchema', () => {
  const base = {
    fullName: 'Ada Lovelace',
    email: 'ada@example.com',
    password: 'Str0ngPass',
    confirmPassword: 'Str0ngPass',
    acceptTerms: true as const,
  }

  it('accepts a complete signup', () => {
    expect(signupSchema.safeParse(base).success).toBe(true)
  })

  it('reports mismatched passwords against the confirm field', () => {
    const result = signupSchema.safeParse({ ...base, confirmPassword: 'Different1' })
    expect(result.success).toBe(false)
    if (!result.success) {
      // The message has to land on the field the user can fix.
      expect(result.error.issues[0]?.path).toEqual(['confirmPassword'])
    }
  })

  it('requires the terms checkbox', () => {
    expect(signupSchema.safeParse({ ...base, acceptTerms: false }).success).toBe(false)
  })
})

describe('loginSchema', () => {
  it('does not impose signup password rules on login', () => {
    // An existing account may predate the current rules; blocking login on them
    // would lock people out of their own data.
    expect(loginSchema.safeParse({ email: 'a@b.com', password: 'old' }).success).toBe(true)
  })

  it('still requires a valid email', () => {
    expect(loginSchema.safeParse({ email: 'nope', password: 'x' }).success).toBe(false)
  })
})

describe('newProjectSchema', () => {
  it('accepts a complete intake', () => {
    expect(newProjectSchema.safeParse(VALID_PROJECT).success).toBe(true)
  })

  it('rejects a thin brand description', () => {
    // The agents reason from this text, so a one-liner produces generic output.
    const result = newProjectSchema.safeParse({
      ...VALID_PROJECT,
      brandDescription: 'We sell coffee.',
    })
    expect(result.success).toBe(false)
  })

  it('requires at least one competitor', () => {
    expect(
      newProjectSchema.safeParse({ ...VALID_PROJECT, competitors: [] }).success,
    ).toBe(false)
  })

  it('caps competitors at five per run', () => {
    const competitors = Array.from({ length: 6 }, (_, index) => ({
      ...VALID_PROJECT.competitors[0],
      name: `Competitor ${index}`,
    }))
    expect(
      newProjectSchema.safeParse({ ...VALID_PROJECT, competitors }).success,
    ).toBe(false)
  })

  it('rejects a competitor URL without a scheme', () => {
    const result = newProjectSchema.safeParse({
      ...VALID_PROJECT,
      competitors: [{ ...VALID_PROJECT.competitors[0], landingPageUrl: 'northbrew.example' }],
    })
    expect(result.success).toBe(false)
  })
})
