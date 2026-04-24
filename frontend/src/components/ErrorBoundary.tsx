import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertCircle } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Uncaught error in React tree:", error, info);
  }

  reset = () => this.setState({ error: null });

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div style={{ padding: 32, maxWidth: 640, margin: "0 auto" }}>
        <div style={{
          background: "#1f1a0e",
          border: "1px solid #f59e0b",
          borderLeft: "3px solid #f59e0b",
          borderRadius: 8,
          padding: 24,
          display: "flex",
          gap: 14,
          alignItems: "flex-start",
        }}>
          <AlertCircle size={22} color="#f59e0b" style={{ flexShrink: 0, marginTop: 1 }} />
          <div style={{ flex: 1 }}>
            <div style={{ color: "#f59e0b", fontWeight: 600, fontSize: 15, marginBottom: 6 }}>
              Something went wrong
            </div>
            <div style={{ color: "#d1d5db", fontSize: 13, lineHeight: 1.5, marginBottom: 12 }}>
              The UI hit an unexpected error. Check the browser console for details and try again.
            </div>
            <pre style={{
              color: "#9ca3af",
              fontSize: 12,
              background: "#0b0d14",
              padding: 12,
              borderRadius: 6,
              overflow: "auto",
              maxHeight: 200,
              margin: "0 0 12px",
            }}>
              {String(this.state.error.message || this.state.error)}
            </pre>
            <button
              onClick={this.reset}
              style={{
                background: "#2563eb",
                color: "white",
                border: "none",
                borderRadius: 6,
                padding: "8px 14px",
                fontSize: 13,
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    );
  }
}
