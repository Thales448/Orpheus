/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.rs"],
  theme: {
    extend: {
      colors: {
        surface: {
          primary: "#0f1117",
          secondary: "#161b22",
          tertiary: "#21262d",
        },
        border: "#30363d",
        accent: "#58a6ff",
      },
      borderRadius: {
        module: "12px",
      },
    },
  },
  plugins: [],
};
