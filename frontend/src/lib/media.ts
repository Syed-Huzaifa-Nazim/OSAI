import { config } from './config'

/**
 * Where an image or video should actually be loaded from.
 *
 * Instagram's CDN answers with `Cross-Origin-Resource-Policy: same-origin`, so
 * a browser refuses to render its media on this origin no matter how it is
 * linked. Those URLs go through the API, which fetches them server-side where
 * that rule does not apply. Every other source -- Daraz, Alibaba, a scraped
 * website -- allows cross-origin use and is loaded directly, so nothing else
 * pays for this.
 */

/** Hosts a browser will not render for us. Matched on the registrable suffix. */
const PROXIED_HOSTS = ['cdninstagram.com', 'fbcdn.net']

export function mediaSrc(url: string): string {
  let host: string
  try {
    host = new URL(url).hostname.toLowerCase()
  } catch {
    return url
  }

  const blocked = PROXIED_HOSTS.some((suffix) => host === suffix || host.endsWith(`.${suffix}`))
  if (!blocked) return url

  return `${config.apiBaseUrl}/scrapers/media?url=${encodeURIComponent(url)}`
}
