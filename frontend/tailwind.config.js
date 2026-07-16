/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: { extend: { colors: { ink: '#07111f', panel: '#0d1b2f', cyan: '#2dd4bf' }, boxShadow: { glow: '0 0 42px rgba(45, 212, 191, .16)' } } },
  plugins: []
}
