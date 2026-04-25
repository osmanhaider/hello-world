import { Sun, Moon, Monitor } from "lucide-react";
import { useTheme, type ThemeMode } from "../theme";

const NEXT: Record<ThemeMode, ThemeMode> = {
  light: "dark",
  dark: "system",
  system: "light",
};

const LABEL: Record<ThemeMode, string> = {
  light: "Light theme",
  dark: "Dark theme",
  system: "Follow system",
};

interface Props {
  compact?: boolean;
}

export default function ThemeToggle({ compact = false }: Props) {
  const { mode, setMode } = useTheme();
  const Icon = mode === "light" ? Sun : mode === "dark" ? Moon : Monitor;
  return (
    <button
      onClick={() => setMode(NEXT[mode])}
      title={`${LABEL[mode]} (click to cycle)`}
      aria-label={`Theme: ${LABEL[mode]}. Click to change.`}
      className="btn-press"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        padding: compact ? "8px 10px" : "8px 12px",
        borderRadius: 8,
        border: "1px solid var(--border)",
        background: "var(--surface-1)",
        color: "var(--text-2)",
        cursor: "pointer",
        fontSize: 13,
      }}
    >
      <Icon size={14} />
      {!compact && (
        <span style={{ textTransform: "capitalize" }}>{mode}</span>
      )}
    </button>
  );
}
