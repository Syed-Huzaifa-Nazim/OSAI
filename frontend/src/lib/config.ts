/**
 * Runtime configuration. Every value comes from a VITE_ env var so nothing
 * environment-specific is baked into the bundle. See .env.example.
 */

function readEnv(key: string): string | undefined {
  const value = import.meta.env[key as keyof ImportMetaEnv]
  return typeof value === 'string' && value.length > 0 ? value : undefined
}

function readBool(key: string, fallback: boolean): boolean {
  const value = readEnv(key)
  if (value === undefined) return fallback
  return value === 'true' || value === '1'
}

export const config = {
  apiBaseUrl: readEnv('VITE_API_BASE_URL') ?? '/api/v1',
  supabaseUrl: readEnv('VITE_SUPABASE_URL'),
  supabaseAnonKey: readEnv('VITE_SUPABASE_ANON_KEY'),

  /**
   * Demo mode. When on, the app serves the seeded sample project from
   * lib/mock/ instead of calling the backend, so the whole 9-stage pipeline can
   * be demonstrated in a defence with no scraping and no LLM spend.
   *
   * It also switches on automatically when Supabase credentials are absent, so
   * a fresh clone runs end-to-end with zero configuration.
   */
  demoMode: readBool('VITE_DEMO_MODE', false),

  /**
   * Which navigation the public marketing site uses. Both are built:
   *   'top', slim glass top navbar (conventional for marketing)
   *   'vertical', the same left rail as the app, for brand consistency
   * Flip the env var (or the in-app switcher in dev) to compare them live.
   */
  marketingNav: (readEnv('VITE_MARKETING_NAV') ?? 'top') as 'top' | 'vertical',

  /** Poll interval for pipeline status, ms. Websockets are the upgrade path. */
  pipelinePollMs: Number(readEnv('VITE_PIPELINE_POLL_MS') ?? 2000),
} as const

/** True when Supabase is configured; false forces the mock auth/data path. */
export const hasSupabase = Boolean(config.supabaseUrl && config.supabaseAnonKey)

/** The single switch the data layer checks before deciding mock vs. live. */
export const isDemoMode = config.demoMode || !hasSupabase
