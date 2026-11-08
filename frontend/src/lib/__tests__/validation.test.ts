import { describe, expect, it } from 'vitest'
import {
  loginSchema,
  newProjectSchema,
  passwordSchema,
  signupSchema,
} from '@/lib/validation'
import { DARAZ_DELL_MOUSE, DARAZ_HP_MOUSE } from '@/test/real-urls'

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
      notes: '',
    },
  ],
  comparisonType: 'website' as const,
  ecommercePlatform: '',
  socialPlatform: '' as const,
}

/** The same intake switched to an e-commerce comparison, with Daraz links. */
const VALID_ECOMMERCE_PROJECT = {
  ...VALID_PROJECT,
  comparisonType: 'ecommerce_product' as const,
  ecommercePlatform: 'daraz',
  brandWebsite: 'https://www.daraz.pk/products/our-kettle-i111-s111.html',
  competitors: [
    {
      ...VALID_PROJECT.competitors[0],
      landingPageUrl: 'https://www.daraz.pk/products/their-kettle-i222-s222.html',
    },
  ],
}

/** The same intake switched to a social comparison on Instagram. */
const VALID_SOCIAL_PROJECT = {
  ...VALID_PROJECT,
  comparisonType: 'social_media' as const,
  socialPlatform: 'instagram' as const,
  brandWebsite: 'https://www.instagram.com/verdantroast',
  competitors: [
    {
      ...VALID_PROJECT.competitors[0],
      landingPageUrl: 'https://instagram.com/northbrew',
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

  it('no longer requires a 40-character description', () => {
    expect(
      newProjectSchema.safeParse({ ...VALID_PROJECT, brandDescription: 'We sell coffee.' }).success,
    ).toBe(true)
  })

  it('still requires a description', () => {
    const result = newProjectSchema.safeParse({ ...VALID_PROJECT, brandDescription: '   ' })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('brandDescription')
  })

  it('caps the description at 120 characters', () => {
    expect(
      newProjectSchema.safeParse({ ...VALID_PROJECT, brandDescription: 'x'.repeat(120) }).success,
    ).toBe(true)
    const result = newProjectSchema.safeParse({ ...VALID_PROJECT, brandDescription: 'x'.repeat(121) })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('brandDescription')
  })

  it('makes who you sell to optional', () => {
    expect(newProjectSchema.safeParse({ ...VALID_PROJECT, targetAudience: '' }).success).toBe(true)
    expect(
      newProjectSchema.safeParse({ ...VALID_PROJECT, targetAudience: undefined }).success,
    ).toBe(true)
  })

  it('caps who you sell to at 120 characters', () => {
    const result = newProjectSchema.safeParse({ ...VALID_PROJECT, targetAudience: 'y'.repeat(121) })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('targetAudience')
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

  it('requires the website on a website comparison', () => {
    const result = newProjectSchema.safeParse({ ...VALID_PROJECT, brandWebsite: '' })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('brandWebsite')
  })
})

describe('newProjectSchema, social media comparisons', () => {
  it('accepts a complete social intake', () => {
    expect(newProjectSchema.safeParse(VALID_SOCIAL_PROJECT).success).toBe(true)
  })

  it('requires a platform', () => {
    const result = newProjectSchema.safeParse({ ...VALID_SOCIAL_PROJECT, socialPlatform: '' })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('socialPlatform')
  })

  it('offers only Facebook and Instagram', () => {
    expect(
      newProjectSchema.safeParse({ ...VALID_SOCIAL_PROJECT, socialPlatform: 'tiktok' }).success,
    ).toBe(false)
  })

  it('requires the platform link', () => {
    const result = newProjectSchema.safeParse({ ...VALID_SOCIAL_PROJECT, brandWebsite: '' })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('brandWebsite')
  })

  it.each([
    ['instagram', 'https://instagram.com/verdantroast', 'https://www.instagram.com/northbrew/'],
    ['instagram', 'https://www.instagram.com/verdantroast/', 'https://m.instagram.com/northbrew'],
  ] as const)('accepts %s links on that platform', (platform, own, competitor) => {
    const result = newProjectSchema.safeParse({
      ...VALID_SOCIAL_PROJECT,
      socialPlatform: platform,
      brandWebsite: own,
      competitors: [{ ...VALID_SOCIAL_PROJECT.competitors[0], landingPageUrl: competitor }],
    })
    expect(result.success).toBe(true)
  })

  it('refuses Facebook until it has a scraper', () => {
    // Listed and disabled on the form; refused here and by the backend too, so
    // a client that skips validation cannot create one either.
    const result = newProjectSchema.safeParse({
      ...VALID_SOCIAL_PROJECT,
      socialPlatform: 'facebook',
      brandWebsite: 'https://www.facebook.com/verdantroast',
      competitors: [
        { ...VALID_SOCIAL_PROJECT.competitors[0], landingPageUrl: 'https://m.facebook.com/northbrew' },
      ],
    })
    expect(issuePaths(result)).toEqual(['socialPlatform'])
    expect(result.success ? '' : result.error.issues[0]?.message).toMatch(/not available yet/i)
  })

  it.each([
    ['the other platform', 'https://www.facebook.com/verdantroast'],
    ['not a social site', 'https://verdantroast.example'],
    ['a lookalike host', 'https://instagram.com.evil.example/page'],
    ['a lookalike name', 'https://notinstagram.com/page'],
  ])('rejects an own link on %s', (_label, link) => {
    const result = newProjectSchema.safeParse({ ...VALID_SOCIAL_PROJECT, brandWebsite: link })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('brandWebsite')
  })

  it("rejects a competitor's link on another platform", () => {
    const result = newProjectSchema.safeParse({
      ...VALID_SOCIAL_PROJECT,
      competitors: [
        { ...VALID_SOCIAL_PROJECT.competitors[0], landingPageUrl: 'https://www.facebook.com/northbrew' },
      ],
    })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('competitors.0.landingPageUrl')
  })
})

describe('newProjectSchema, long links', () => {
  it('accepts the real 1,000+ character Daraz links that used to be "too long"', () => {
    expect(DARAZ_DELL_MOUSE.length).toBeGreaterThan(1000)
    expect(DARAZ_HP_MOUSE.length).toBeGreaterThan(1000)

    const result = newProjectSchema.safeParse({
      ...VALID_ECOMMERCE_PROJECT,
      brandWebsite: DARAZ_DELL_MOUSE,
      competitors: [{ ...VALID_ECOMMERCE_PROJECT.competitors[0], landingPageUrl: DARAZ_HP_MOUSE }],
    })
    expect(issuePaths(result)).toEqual([])
    // Kept exactly as pasted.
    expect(result.success && result.data.brandWebsite).toBe(DARAZ_DELL_MOUSE)
  })

  it.each([
    ['website', VALID_PROJECT, 'https://verdantroast.example/', 'https://northbrew.example/'],
    [
      'social media',
      VALID_SOCIAL_PROJECT,
      'https://www.instagram.com/verdantroast',
      'https://instagram.com/northbrew',
    ],
  ] as const)('accepts long links on the %s tab too', (_tab, base, own, competitor) => {
    const tracking = `?utm_source=search&clickTrackInfo=${'a'.repeat(1500)}`
    const result = newProjectSchema.safeParse({
      ...base,
      brandWebsite: own + tracking,
      competitors: [{ ...base.competitors[0], landingPageUrl: competitor + tracking }],
    })
    expect(issuePaths(result)).toEqual([])
  })

  it('still bounds a pathological link', () => {
    const result = newProjectSchema.safeParse({
      ...VALID_PROJECT,
      brandWebsite: `https://verdantroast.example/?q=${'a'.repeat(9000)}`,
    })
    expect(issuePaths(result)).toContain('brandWebsite')
  })
})

describe('newProjectSchema, e-commerce comparisons', () => {
  it('accepts a complete e-commerce intake', () => {
    expect(newProjectSchema.safeParse(VALID_ECOMMERCE_PROJECT).success).toBe(true)
  })

  it('requires a platform', () => {
    const result = newProjectSchema.safeParse({
      ...VALID_ECOMMERCE_PROJECT,
      ecommercePlatform: '',
    })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('ecommercePlatform')
  })

  it('requires the user to supply their own listing', () => {
    // Without a baseline there is nothing to compare the competitor against.
    const result = newProjectSchema.safeParse({
      ...VALID_ECOMMERCE_PROJECT,
      brandWebsite: '',
    })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('brandWebsite')
  })

  it('rejects an own link that is not on the chosen platform', () => {
    const result = newProjectSchema.safeParse({
      ...VALID_ECOMMERCE_PROJECT,
      brandWebsite: 'https://www.amazon.com/dp/B0EXAMPLE',
    })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('brandWebsite')
  })

  it('rejects a competitor link that is not on the chosen platform', () => {
    const result = newProjectSchema.safeParse({
      ...VALID_ECOMMERCE_PROJECT,
      competitors: [
        {
          ...VALID_ECOMMERCE_PROJECT.competitors[0],
          landingPageUrl: 'https://www.ebay.com/itm/12345',
        },
      ],
    })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('competitors.0.landingPageUrl')
  })

  it('accepts any Daraz country domain, not just .pk', () => {
    expect(
      newProjectSchema.safeParse({
        ...VALID_ECOMMERCE_PROJECT,
        brandWebsite: 'https://www.daraz.com.bd/products/x-i1-s1.html',
      }).success,
    ).toBe(true)
  })

  it('rejects the same listing on both sides, ignoring tracking parameters', () => {
    // Copied out of search results the same product carries a different query
    // string every time, so a string comparison would miss the duplicate.
    const result = newProjectSchema.safeParse({
      ...VALID_ECOMMERCE_PROJECT,
      competitors: [
        {
          ...VALID_ECOMMERCE_PROJECT.competitors[0],
          landingPageUrl:
            'https://www.daraz.pk/products/our-kettle-i111-s111.html?clickTrackInfo=abc&spm=a2a0e',
        },
      ],
    })
    expect(result.success).toBe(false)
    expect(issuePaths(result)).toContain('competitors.0.landingPageUrl')
  })

  it('ignores the platform rules once the type changes back', () => {
    // A stale platform left in form state must not fail a website project.
    expect(
      newProjectSchema.safeParse({
        ...VALID_ECOMMERCE_PROJECT,
        comparisonType: 'website' as const,
        brandWebsite: 'https://verdantroast.example',
        competitors: VALID_PROJECT.competitors,
      }).success,
    ).toBe(true)
  })
})

describe('newProjectSchema, Alibaba comparisons', () => {
  const MOUSE =
    'https://www.alibaba.com/product-detail/Mini-Wireless-Mouse-Ergonomic-4-Buttons_1601364965690.html?spm=a2700.galleryofferlist.normal_offer.d_title.1'
  const GAMING =
    'https://www.alibaba.com/product-detail/MLOONG-MX302-Ultra-Lightweight-Wireless-Gaming_1601688290824.html'

  const alibaba = (own: string, competitor: string) => ({
    ...VALID_ECOMMERCE_PROJECT,
    ecommercePlatform: 'alibaba',
    brandWebsite: own,
    competitors: [{ ...VALID_ECOMMERCE_PROJECT.competitors[0], landingPageUrl: competitor }],
  })

  it('accepts two different Alibaba products', () => {
    expect(issuePaths(newProjectSchema.safeParse(alibaba(MOUSE, GAMING)))).toEqual([])
  })

  it.each([
    ['a mobile link', 'https://m.alibaba.com/product/1601688290824/MLOONG-MX302.html'],
    ['a bare mobile link', 'https://m.alibaba.com/product/1601688290824.html'],
    ['a regional site', 'https://french.alibaba.com/product-detail/Souris-Gaming_1601688290824.html'],
  ])('accepts %s', (_label, link) => {
    expect(issuePaths(newProjectSchema.safeParse(alibaba(MOUSE, link)))).toEqual([])
  })

  it.each([
    ['a Daraz link', 'https://www.daraz.pk/products/their-kettle-i222-s222.html'],
    ['a lookalike host', 'https://alibaba.com.evil.example/product-detail/Mouse_1601688290824.html'],
    ['a lookalike name', 'https://notalibaba.com/product-detail/Mouse_1601688290824.html'],
    ['a search page', 'https://www.alibaba.com/showroom/wireless-mouse.html'],
    ['a supplier storefront', 'https://kingmega.en.alibaba.com/productlist.html'],
  ])('rejects %s', (_label, link) => {
    const result = newProjectSchema.safeParse(alibaba(MOUSE, link))
    expect(issuePaths(result)).toEqual(['competitors.0.landingPageUrl'])
    expect(result.success ? '' : result.error.issues[0]?.message).toMatch(/alibaba product link/i)
  })

  it.each([
    ['tracking parameters', MOUSE.replace('d_title.1', 'd_image.9')],
    ['a reworded title', 'https://www.alibaba.com/product-detail/Other-Title_1601364965690.html'],
    ['the mobile site', 'https://m.alibaba.com/product/1601364965690/Mini-Mouse.html'],
  ])('recognises the same product behind %s', (_label, sameProduct) => {
    const result = newProjectSchema.safeParse(alibaba(MOUSE, sameProduct))
    expect(issuePaths(result)).toEqual(['competitors.0.landingPageUrl'])
    expect(result.success ? '' : result.error.issues[0]?.message).toMatch(/same listing/i)
  })
})

/** The dotted field paths a failed parse complained about. */
function issuePaths(result: ReturnType<typeof newProjectSchema.safeParse>): string[] {
  return result.success ? [] : result.error.issues.map((issue) => issue.path.join('.'))
}
