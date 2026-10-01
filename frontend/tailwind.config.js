/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
        serif: ["'Source Serif 4'", "Georgia", "serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      colors: {
        legal: {
          bg: "#F7F6F2",
          surface: "#FFFFFF",
          primary: "#17243A",
          secondary: "#626B78",
          accent: "#176B68",
          "accent-hover": "#125552",
          "accent-subtle": "#E8F3EF",
          border: "#DFE3E6",
          "attention-bg": "#FFF3DC",
          "attention-text": "#805A16",
          navy: "#0B132B",
          "sidebar-navy": "#0F172A",
          error: "#B13B3B",
        },
        brand: {
          50:  "#e8f3ef",
          100: "#c8e2da",
          200: "#99c6b8",
          300: "#6aa996",
          400: "#3b8d74",
          500: "#176b68",
          600: "#125552",
          700: "#0e403d",
          800: "#092a28",
          900: "#051514",
        },
      },
      borderRadius: {
        lg: "0.5rem",
        xl: "0.75rem",  /* 12px */
        "2xl": "0.875rem", /* 14px */
        "3xl": "1.25rem",
      },
      boxShadow: {
        subtle: "0 1px 3px 0 rgba(23, 36, 58, 0.04), 0 1px 2px -1px rgba(23, 36, 58, 0.03)",
        card: "0 2px 8px -2px rgba(23, 36, 58, 0.06), 0 1px 3px -1px rgba(23, 36, 58, 0.04)",
        document: "0 4px 20px -2px rgba(23, 36, 58, 0.08), 0 1px 4px -1px rgba(23, 36, 58, 0.04)",
        elevated: "0 12px 32px -4px rgba(23, 36, 58, 0.12), 0 4px 12px -2px rgba(23, 36, 58, 0.06)",
        glow: "0 0 0 3px rgba(23, 107, 104, 0.2)",
      },
    },
  },
  plugins: [],
};
