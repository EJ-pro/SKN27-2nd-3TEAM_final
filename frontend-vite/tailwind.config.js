/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sakura: {
          50: '#FFF0F5',
          100: '#FFD6E7',
          200: '#FFB3D1',
          400: '#F472A8',
          600: '#C94E80',
          800: '#8B2255',
        },
        spring: {
          50: '#F0FAF0',
          100: '#C8EDC0',
          200: '#97D47F',
          400: '#55A83A',
          600: '#2E7D1A',
          800: '#16500A',
        }
      }
    },
  },
  plugins: [],
}
