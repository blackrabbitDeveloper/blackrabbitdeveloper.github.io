/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './privacy.html', './js/**/*.js'],
  theme: {
    extend: {
      colors: {
        // Supabase-inspired green accent
        brand: {
          DEFAULT: '#3ECF8E',
          light: '#4ADE80',
          dark: '#22C55E',
        },
        surface: {
          DEFAULT: '#1c1c1c',
          elevated: '#252525',
          border: 'rgba(255,255,255,0.08)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
};
