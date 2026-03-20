/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        /* Primary — dark navy, matching the app's #10243f usage */
        primary: {
          50: '#f0f4f9',
          100: '#d9e3ef',
          200: '#b8c9de',
          300: '#8fabc8',
          400: '#6889ad',
          500: '#4a6b91',
          600: '#365174',
          700: '#283e5a',
          800: '#1c2f45',
          900: '#10243f',
          950: '#081526',
        },
        /* Canvas — warm background tones */
        canvas: {
          DEFAULT: '#f6f2e8',
          soft: '#fcfbf8',
        },
        /* Ink — text hierarchy */
        ink: {
          DEFAULT: '#101828',
          secondary: '#344054',
          muted: '#5f6c7b',
          soft: '#98a2b3',
        },
        /* Accent — warm orange */
        accent: {
          DEFAULT: '#ff6b2c',
          strong: '#8b360f',
          soft: '#ffedd5',
        },
        /* Signal — teal */
        signal: {
          DEFAULT: '#0f766e',
          soft: '#d9fbf5',
        },
      },
      borderRadius: {
        'glass-sm': '0.625rem',
        'glass': '0.875rem',
        'glass-lg': '1.25rem',
        'glass-xl': '1.75rem',
      },
      boxShadow: {
        'glass-xs': '0 1px 2px rgba(15,23,42,0.05)',
        'glass-sm': '0 2px 8px -2px rgba(15,23,42,0.08), 0 1px 2px rgba(15,23,42,0.04)',
        'glass-md': '0 8px 24px -8px rgba(15,23,42,0.12), 0 2px 6px -1px rgba(15,23,42,0.06)',
        'glass': '0 20px 50px -20px rgba(15,23,42,0.2), 0 4px 12px -4px rgba(15,23,42,0.06)',
        'glass-lg': '0 30px 60px -24px rgba(15,23,42,0.25), 0 6px 16px -6px rgba(15,23,42,0.08)',
      },
      backdropBlur: {
        'glass': '20px',
        'glass-strong': '24px',
      },
    },
  },
  plugins: [require('@tailwindcss/typography')],
}
