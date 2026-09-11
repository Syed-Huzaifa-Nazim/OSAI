import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
})

// jsdom implements neither of these, and both are used by the layout code.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }),
})

window.HTMLElement.prototype.scrollIntoView = vi.fn()
// jsdom implements neither of these on Element; the pipeline stepper scrolls
// its own strip with them.
window.HTMLElement.prototype.scrollTo = vi.fn()

/**
 * Radix's Select drives its trigger with Pointer Events, and jsdom implements
 * no part of the pointer-capture API. Without these, opening a Select throws
 * `target.hasPointerCapture is not a function` and the listbox never mounts,
 * so every dropdown looks empty in a test while working fine in a browser.
 */
window.HTMLElement.prototype.hasPointerCapture = vi.fn(() => false)
window.HTMLElement.prototype.setPointerCapture = vi.fn()
window.HTMLElement.prototype.releasePointerCapture = vi.fn()

/**
 * jsdom and Node disagree about what an AbortSignal is.
 *
 * jsdom installs its own `AbortController`/`AbortSignal` over the globals,
 * while `Request` stays Node's (jsdom implements no fetch). Node's undici
 * captured its own `AbortSignal` class at load time, so it rejects jsdom's with
 * `RequestInit: Expected signal ("AbortSignal {}") to be an instance of
 * AbortSignal`. React Router builds a Request per navigation, so every
 * link-click test dies on it. Node's originals are gone by the time this file
 * runs -- deleting the jsdom ones leaves nothing behind -- so the only seam
 * left is Request itself.
 *
 * The signal is dropped rather than converted. Nothing here asserts abort
 * behaviour: these tests click a link and expect a page. If a test is ever
 * added that depends on a navigation being *cancelled*, this shim would hide
 * the failure, so revisit it then.
 */
const NativeRequest = globalThis.Request
globalThis.Request = class extends NativeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    if (init && 'signal' in init) {
      const { signal: _dropped, ...rest } = init
      super(input, rest)
      return
    }
    super(input, init)
  }
} as typeof Request

class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
window.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver

/**
 * jsdom has no IntersectionObserver, and Framer Motion's `whileInView` needs
 * one. Without this stub, any page using a scroll-reveal renders nothing,
 * which looks exactly like a broken route and sent me hunting the wrong bug.
 *
 * The stub reports every observed element as intersecting, so scroll-revealed
 * content is present and assertable.
 */
class IntersectionObserverStub implements IntersectionObserver {
  readonly root: Element | Document | null = null
  readonly rootMargin: string = '0px'
  readonly thresholds: ReadonlyArray<number> = [0]

  private readonly callback: IntersectionObserverCallback

  constructor(callback: IntersectionObserverCallback) {
    this.callback = callback
  }

  observe(target: Element): void {
    this.callback(
      [
        {
          isIntersecting: true,
          intersectionRatio: 1,
          target,
          boundingClientRect: target.getBoundingClientRect(),
          intersectionRect: target.getBoundingClientRect(),
          rootBounds: null,
          time: 0,
        } as IntersectionObserverEntry,
      ],
      this,
    )
  }

  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return []
  }
}
window.IntersectionObserver = IntersectionObserverStub as unknown as typeof IntersectionObserver
