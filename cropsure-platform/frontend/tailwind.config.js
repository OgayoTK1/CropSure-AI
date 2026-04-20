/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#1D9E75',
          light: '#2EC08E',
          dark: '#157A5A',
        },
      },
      animation: {
        'pulse-fast': 'pulse 0.8s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}