import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('UI render error:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-50 p-6">
          <div className="mx-auto max-w-2xl rounded-lg border border-red-200 bg-white p-6 shadow-sm">
            <h1 className="text-xl font-bold text-red-700">Something went wrong</h1>
            <p className="mt-2 text-sm text-gray-600">
              The interface hit an unexpected rendering error. Please reload the page.
            </p>
            {this.state.error?.message && (
              <pre className="mt-4 overflow-auto rounded bg-red-50 p-3 text-sm text-red-700">
                {this.state.error.message}
              </pre>
            )}
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-4 rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white hover:bg-blue-700"
            >
              Reload
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
