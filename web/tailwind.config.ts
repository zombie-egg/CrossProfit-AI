import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)", foreground: "var(--foreground)",
        card: { DEFAULT: "var(--card)", foreground: "var(--card-foreground)" },
        popover: { DEFAULT: "var(--popover)", foreground: "var(--popover-foreground)" },
        primary: { DEFAULT: "var(--primary)", foreground: "var(--primary-foreground)" },
        secondary: { DEFAULT: "var(--secondary)", foreground: "var(--secondary-foreground)" },
        muted: { DEFAULT: "var(--muted)", foreground: "var(--muted-foreground)" },
        accent: { DEFAULT: "var(--accent)", foreground: "var(--accent-foreground)" },
        border: "var(--border)", input: "var(--input)", ring: "var(--ring)", destructive: "var(--destructive)",
        sidebar: { DEFAULT: "var(--sidebar)", foreground: "var(--sidebar-foreground)", primary: "var(--sidebar-primary)", "primary-foreground": "var(--sidebar-primary-foreground)", accent: "var(--sidebar-accent)", "accent-foreground": "var(--sidebar-accent-foreground)", border: "var(--sidebar-border)", ring: "var(--sidebar-ring)" },
      },
      borderRadius: { xl: "var(--radius)", lg: "calc(var(--radius) - 2px)" },
    },
  },
  plugins: [],
};
export default config;
