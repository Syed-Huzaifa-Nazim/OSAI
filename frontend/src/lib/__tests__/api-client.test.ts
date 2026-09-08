import { describe, expect, it } from 'vitest'
import { ApiError, errorMessage } from '@/lib/api-client'

describe('ApiError', () => {
  it('reads the message, code and field errors from the envelope', () => {
    const error = new ApiError(
      422,
      {
        error: {
          code: 'validation_error',
          message: 'Some of the values you submitted are not valid.',
          fields: { brandDescription: 'Too short' },
          requestId: 'req-1',
        },
      },
      'fallback',
    )

    expect(error.status).toBe(422)
    expect(error.code).toBe('validation_error')
    expect(error.fields.brandDescription).toBe('Too short')
    expect(error.requestId).toBe('req-1')
  })

  it('falls back when the body is missing or unparseable', () => {
    const error = new ApiError(500, null, 'Request failed with status 500')
    expect(error.message).toBe('Request failed with status 500')
    expect(error.code).toBe('unknown_error')
    expect(error.fields).toEqual({})
  })

  it('identifies auth failures', () => {
    expect(new ApiError(401, null, 'x').isAuthError).toBe(true)
    expect(new ApiError(403, null, 'x').isAuthError).toBe(true)
    expect(new ApiError(404, null, 'x').isAuthError).toBe(false)
  })

  it('treats server and rate-limit failures as retryable, validation as not', () => {
    // The query client keys its retry policy off this, so a wrong answer here
    // means either pointless retries or a lost recovery.
    expect(new ApiError(500, null, 'x').isRetryable).toBe(true)
    expect(new ApiError(429, null, 'x').isRetryable).toBe(true)
    expect(new ApiError(422, null, 'x').isRetryable).toBe(false)
    expect(new ApiError(404, null, 'x').isRetryable).toBe(false)
  })
})

describe('errorMessage', () => {
  it('unwraps errors and gives unknown throws a safe default', () => {
    expect(errorMessage(new Error('boom'))).toBe('boom')
    expect(errorMessage('a string')).toBe('Something went wrong. Please try again.')
  })
})
