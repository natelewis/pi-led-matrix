import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from './Button';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, message: '' };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      message: error.message || 'An unexpected rendering error occurred.',
    };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('LED Matrix Studio ErrorBoundary:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-surface-950 px-6 text-center text-slate-200">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-rose-500/35 bg-rose-500/12 text-rose-400">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <div className="max-w-md space-y-1">
            <h1 className="text-base font-semibold text-white">Something went wrong</h1>
            <p className="text-xs text-slate-400">{this.state.message}</p>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => window.location.reload()}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
          >
            Reload Studio
          </Button>
        </div>
      );
    }
    return this.props.children;
  }
}
