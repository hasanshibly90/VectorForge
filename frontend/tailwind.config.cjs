/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        accent: {
          50: "#f3f1ff",
          100: "#e9e4ff",
          200: "#d5cdff",
          300: "#b5a6ff",
          400: "#9580ff",
          500: "#7c6af6",
          600: "#6b47ee",
          700: "#5c35da",
          800: "#4d2cb7",
          900: "#402695",
          950: "#261566",
        },
        dark: {
          50: "#f5f5f7",
          100: "#e4e4e9",
          200: "#c8c8d2",
          300: "#a3a3b3",
          400: "#7a7a8e",
          500: "#5c5c70",
          600: "#46465a",
          700: "#2e2e3e",
          800: "#1e1e2a",
          850: "#16161e",
          900: "#0d0d14",
          950: "#0a0a0f",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      boxShadow: {
        glow: "0 0 20px rgba(124,106,246,0.15)",
        "glow-lg": "0 0 40px rgba(124,106,246,0.2)",
      },
    },
  },
  plugins: [],
};
