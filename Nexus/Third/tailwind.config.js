/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.rs"],
  theme: {
    extend: {
      colors: {
        surface: {
          primary: "#060b14",
          secondary: "#0d1321",
          tertiary: "#0f1624",
        },
        border: "rgba(56, 126, 209, 0.18)",
        accent: {
          cyan: "#22d3ee",
          purple: "#a78bfa",
          green: "#34d399",
          yellow: "#facc15",
          red: "#f87171",
        },
      },
      borderRadius: {
        panel: "10px",
      },
      boxShadow: {
        glow: "0 0 20px rgba(34, 211, 238, 0.06)",
        "glow-strong": "0 0 24px rgba(34, 211, 238, 0.12)",
      },
    },
  },
  plugins: [],
};
