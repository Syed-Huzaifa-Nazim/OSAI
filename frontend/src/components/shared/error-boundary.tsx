import { Component, type ErrorInfo, type ReactNode } from 'react'
import { ErrorState } from './state-views'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  error: Error | null
}

/**
 * Catches render-time crashes so one broken panel cannot take down the shell.
 * Route-level boundaries wrap each page; see app/router.tsx.
 */
export class ErrorBoundary extends Component<Props, State> {
  override state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // Kept as console.error deliberately: the app has no error-reporting sink
    // yet. docs/error-handling.md tracks wiring this to a real one.
    console.error('Unhandled render error', error, info.componentStack)
  }

  override render(): ReactNode {
    if (this.state.error) {
      return (
        this.props.fallback ?? (
          <div className="p-6">
            <ErrorState
              title="This section failed to render"
              message={this.state.error.message}
              onRetry={() => {
                this.setState({ error: null })
              }}
            />
          </div>
        )
      )
    }
    return this.props.children
  }
}
