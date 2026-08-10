/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        term: {
          bg: '#0d1117', panel: '#161b22', border: '#21262d',
          text: '#c9d1d9', dim: '#8b949e', amber: '#f0b90b',
          up: '#f6465d', down: '#0ecb81',
        },
      },
      fontFamily: {
        mono: ['ui-monospace', 'SF Mono', 'Menlo', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
