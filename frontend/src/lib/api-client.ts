import { config } from './config'
import { getAccessToken } from './supabase'

/**
 * The error envelope every FastAPI route returns on failure.
 * Documented in docs/error-handling.md, backend and frontend agree on it.
 */
export interface ApiErrorBody {
  error: {
    code: string
    message: string
    /** Field-level messages, keyed by form field name. Drives per-field errors. */
    fields?: Record<string, string>
    requestId?: string
  }
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: Record<string, string>
  readonly requestId: string | undefined

  constructor(status: number, body: Partial<ApiErrorBody> | null, fallback: string) {
    const detail = body?.error
    super(detail?.message ?? fallback)
    this.name = 'ApiError'
    this.status = status
    this.code = detail?.code ?? 'unknown_error'
    this.fields = detail?.fields ?? {}
    this.requestId = detail?.requestId
  }

  /** True for the cases where re-authenticating is the fix. */
  get isAuthError(): boolean {
    return this.status === 401 || this.status === 403
  }

  /** True when the user can reasonably retry the same action. */
  get isRetryable(): boolean {
    return this.status >= 500 || this.status === 408 || this.status === 429
  }
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  /** Skip the Authorization header (used by the public contact endpoint). */
  anonymous?: boolean
  signal?: AbortSignal
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, anonymous, headers, ...rest } = options

  const finalHeaders = new Headers(headers)
  if (body !== undefined && !finalHeaders.has('Content-Type')) {
    finalHeaders.set('Content-Type', 'application/json')
  }
  if (!anonymous) {
    const token = await getAccessToken()
    if (token) finalHeaders.set('Authorization', `Bearer ${token}`)
  }

  let response: Response
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      ...rest,
      headers: finalHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (cause) {
    // Network-level failure: no response at all. Surfaced as a retryable 0.
    throw new ApiError(0, null, 'Could not reach the OptiStratixAI API. Check your connection.')
  }

  if (response.status === 204) return undefined as T

  const text = await response.text()
  const payload: unknown = text ? safeJsonParse(text) : null

  if (!response.ok) {
    throw new ApiError(
      response.status,
      payload as ApiErrorBody | null,
      `Request failed with status ${response.status}`,
    )
  }

  return payload as T
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'POST', body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PATCH', body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'PUT', body }),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>(path, { ...options, method: 'DELETE' }),
}

/**
 * Downloads a file from a protected endpoint (it needs the login token, so a plain link would be refused)
 * and saves it in the browser under `filename`.
 */
/**
 * Opens a file from the API (e.g. a PDF report) in a browser tab. `tab` must be opened by the click itself
 * (window.open before any await), or the browser blocks it as a pop-up; without it the file is downloaded instead.
 */
export async function openFile(path: string, filename: string, tab: Window | null): Promise<void> {
  const headers = new Headers()
  const token = await getAccessToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  let response: Response
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, { headers })
  } catch {
    tab?.close()
    throw new ApiError(0, null, 'Could not reach the OptiStratixAI API. Check your connection.')
  }
  if (!response.ok) {
    tab?.close()
    const text = await response.text()
    throw new ApiError(
      response.status,
      (text ? safeJsonParse(text) : null) as ApiErrorBody | null,
      `Opening the report failed with status ${response.status}`,
    )
  }
  const url = URL.createObjectURL(await response.blob())
  if (tab) {
    tab.location.href = url
    return
  }
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const headers = new Headers()
  const token = await getAccessToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  let response: Response
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, { headers })
  } catch {
    throw new ApiError(0, null, 'Could not reach the OptiStratixAI API. Check your connection.')
  }
  if (!response.ok) {
    const text = await response.text()
    throw new ApiError(
      response.status,
      (text ? safeJsonParse(text) : null) as ApiErrorBody | null,
      `Download failed with status ${response.status}`,
    )
  }
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

/** Normalises anything thrown into a message safe to show a user. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Something went wrong. Please try again.'
}
