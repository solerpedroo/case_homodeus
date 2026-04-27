/**
 * EN: Tailwind theme — editorial dark palette (bg/ink/accent), custom fonts
 *     via CSS variables from next/font in layout.tsx.
 * PT: Tema Tailwind — paleta escura editorial, fontes via variáveis do layout.
 */
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
          DEFAULT: "#070709",
          subtle: "#0b0b0e",
          panel: "#0f0f12",
          elevated: "#17171c",
        },
        ink: {
          DEFAULT: "#f0f0f3",
          muted: "#9ea0a8",
          dim: "#5d5f68",
        },
        accent: {
          DEFAULT: "#4d7fff",
          glow: "#7aa1ff",
          soft: "rgba(77,127,255,0.10)",
        },
        success: { DEFAULT: "#22c55e", soft: "rgba(34,197,94,0.12)" },
        warning: { DEFAULT: "#f59e0b", soft: "rgba(245,158,11,0.12)" },
        danger:  { DEFAULT: "#ef4444", soft: "rgba(239,68,68,0.12)" },
        border: {
          DEFAULT: "rgba(255,255,255,0.065)",
          strong: "rgba(255,255,255,0.13)",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-jetbrains)", "ui-monospace", "SFMono-Regular"],
      },
      letterSpacing: {
        tightest: "-0.025em",
        marker: "0.14em",
      },
      keyframes: {
        "fade-in": { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "blink": {
          "0%,49%": { opacity: "1" },
          "50%,100%": { opacity: "0" },
        },
        "dot-fade": {
          "0%,100%": { opacity: "0.25" },
          "50%": { opacity: "1" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.25s ease-out",
        "slide-up": "slide-up 0.35s cubic-bezier(0.2,0.8,0.2,1)",
        "blink": "blink 1.05s steps(1) infinite",
        "dot-fade": "dot-fade 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
