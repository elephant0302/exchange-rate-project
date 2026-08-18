/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,ts}"],
  theme: {
    extend: {
      colors: {
        canvas: "#090D14",
        card: "#111827",
        panel: "#172033",
        ink: "#F3F4F6",
        mute: "#94A3B8",
        actual: "#22D3EE",
        forecast: "#F59E0B",
        up: "#EF4444",
        down: "#3B82F6",
        ok: "#22C55E",
        warn: "#F59E0B",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Pretendard", "Apple SD Gothic Neo", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};
