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
