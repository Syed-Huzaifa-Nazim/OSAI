import { createClient, type SupabaseClient } from '@supabase/supabase-js'
import { config, hasSupabase } from './config'

/**
 * Supabase browser client. Null when credentials are absent. The app then
 * runs on the mock auth path (see stores/auth-store.ts) so a fresh clone still
 * boots. Never import this directly in components; go through the auth store.
 */
export const supabase: SupabaseClient | null = hasSupabase
  ? createClient(config.supabaseUrl as string, config.supabaseAnonKey as string, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        storageKey: 'optistratix-auth',
      },
    })
  : null

/** The JWT the FastAPI middleware verifies. Null when signed out or in demo. */
export async function getAccessToken(): Promise<string | null> {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}
