/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0f1d",
        card: "#111827",
        border: "#1f293d",
        accent: "#10b981", // Emerald accent
        accentLight: "#34d399",
      },
    },
  },
  plugins: [],
};
