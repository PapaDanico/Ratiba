import { Component } from "react";
import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error("Error caught by boundary:", error, errorInfo);
  }

  override render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-dn-steel-lt via-white to-dn-steel-lt px-4">
          <div className="text-center space-y-6 max-w-md">
            <div className="space-y-2">
              <h1 className="text-4xl font-bold text-dn-steel">Oops!</h1>
              <h2 className="text-2xl font-bold text-dn-dark">Something went wrong</h2>
              <p className="text-dn-muted">
                {this.state.error?.message || "An unexpected error occurred."}
              </p>
            </div>
            <div className="flex gap-4 justify-center">
              <button
                onClick={() => (window.location.href = "/")}
                className="px-6 py-3 rounded-lg bg-dn-steel text-white font-medium hover:opacity-90 transition-opacity"
              >
                Go Home
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-6 py-3 rounded-lg border-2 border-dn-steel text-dn-steel font-medium hover:bg-dn-steel hover:text-white transition-colors"
              >
                Reload Page
              </button>
            </div>
            {import.meta.env.DEV && (
              <details className="mt-6 text-left text-sm text-dn-muted">
                <summary className="cursor-pointer font-mono">Error details</summary>
                <pre className="mt-2 bg-dn-fog p-3 rounded overflow-auto text-xs">
                  {this.state.error?.stack}
                </pre>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
