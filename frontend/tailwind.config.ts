import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        bg: {
          DEFAULT: "#0a0a0f",
          subtle: "#10101a",
          panel: "#14141f",
          elevated: "#1c1c2a",
        },
        ink: {
          DEFAULT: "#e8e8ee",
          muted: "#9a9aaa",
          dim: "#6b6b7d",
        },
        accent: {
          DEFAULT: "#7c5cff",
          glow: "#a385ff",
          soft: "rgba(124,92,255,0.15)",
        },
        success: { DEFAULT: "#2dd4bf", soft: "rgba(45,212,191,0.15)" },
        warning: { DEFAULT: "#f59e0b", soft: "rgba(245,158,11,0.15)" },
        danger:  { DEFAULT: "#ef4444", soft: "rgba(239,68,68,0.15)" },
        border: { DEFAULT: "rgba(255,255,255,0.08)", strong: "rgba(255,255,255,0.16)" },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-jetbrains)", "ui-monospace", "SFMono-Regular"],
      },
      keyframes: {
        "fade-in": { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        pulseGlow: {
          "0%,100%": { boxShadow: "0 0 12px rgba(124,92,255,0.30)" },
          "50%":     { boxShadow: "0 0 24px rgba(124,92,255,0.55)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.25s ease-out",
        "slide-up": "slide-up 0.35s cubic-bezier(0.2,0.8,0.2,1)",
        shimmer: "shimmer 1.6s linear infinite",
        "pulse-glow": "pulseGlow 2s ease-in-out infinite",
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(circle at 30% 20%, rgba(124,92,255,0.08), transparent 60%), radial-gradient(circle at 80% 80%, rgba(45,212,191,0.06), transparent 60%)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
