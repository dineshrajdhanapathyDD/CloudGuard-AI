/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Dark navy / slate operations palette with restrained cyan accents.
        ink: "#e7ecf6",
        mute: "#8d9ab5",
        bg: "#0a0e1a",
        panel: "#111a2e",
        panel2: "#0f1628",
        line: "#223052",
        cyan: "#39c0ed",
        orange: "#ff9900",
        proceed: "#34d399",
        clarify: "#fbbf24",
        deny: "#f87171",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      keyframes: {
        pop: { "0%": { transform: "scale(.97)", opacity: "0.2" }, "100%": { transform: "none", opacity: "1" } },
        pulseline: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.4" } },
      },
      animation: {
        pop: "pop .35s ease",
        pulseline: "pulseline 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
