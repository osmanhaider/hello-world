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
        <div className="slide-up" style={{
          background: "var(--warning-soft)",
          border: "1px solid var(--warning)",
          borderLeft: "3px solid var(--warning)",
          borderRadius: 12,
          padding: 24,
          display: "flex",
          gap: 14,
          alignItems: "flex-start",
        }}>
          <AlertCircle size={22} style={{ flexShrink: 0, marginTop: 1, color: "var(--warning)" }} />
          <div style={{ flex: 1 }}>
            <div style={{ color: "var(--warning)", fontWeight: 600, fontSize: 15, marginBottom: 6 }}>
              Something went wrong
            </div>
            <div style={{ color: "var(--text-1)", fontSize: 13, lineHeight: 1.5, marginBottom: 12 }}>
              The UI hit an unexpected error. Check the browser console for details and try again.
            </div>
            <pre style={{
              color: "var(--text-2)",
              fontSize: 12,
              background: "var(--surface-2)",
              padding: 12,
              borderRadius: 8,
              overflow: "auto",
              maxHeight: 200,
              margin: "0 0 12px",
            }}>
              {String(this.state.error.message || this.state.error)}
            </pre>
            <button
              onClick={this.reset}
              className="btn-press"
              style={{
                background: "var(--accent)",
                color: "var(--text-on-accent)",
                border: "none",
                borderRadius: 8,
                padding: "8px 14px",
                fontSize: 13,
                fontWeight: 500,
                cursor: "pointer",
                boxShadow: "var(--shadow-sm)",
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
