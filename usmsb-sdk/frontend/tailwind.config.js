/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  // Safelist dynamic color classes
  safelist: [
    { pattern: /text-neon-(blue|purple|pink|green|yellow|orange|red)/ },
    { pattern: /bg-neon-(blue|purple|pink|green|yellow|orange|red)/ },
    { pattern: /border-neon-(blue|purple|pink|green|yellow|orange|red)/ },
    // Light mode semantic colors
    { pattern: /text-light-/ },
    { pattern: /bg-light-/ },
    { pattern: /border-light-/ },
  ],
  theme: {
    extend: {
      colors: {
        // Light mode semantic colors - AI 科技风格
        light: {
          bg: {
            primary: '#ffffff',
            secondary: '#f0f9ff',
            tertiary: '#e0f2fe',
            card: '#ffffff',
          },
          text: {
            primary: '#1e3a8a',
            secondary: '#1d4ed8',
            muted: '#3b82f6',
          },
          border: '#bfdbfe',
        },
        // Cyberpunk color system
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        secondary: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
        // Neon colors - flattened for direct class access (text-neon-blue, bg-neon-green, etc.)
        'neon-blue': '#00f5ff',
        'neon-purple': '#bf00ff',
        'neon-pink': '#ff00ff',
        'neon-green': '#00ff88',
        'neon-yellow': '#ffff00',
        'neon-orange': '#ff6600',
        'neon-red': '#ff0040',
        // Neon colors (nested for neon.blue access)
        neon: {
          blue: '#00f5ff',
          purple: '#bf00ff',
          pink: '#ff00ff',
          green: '#00ff88',
          yellow: '#ffff00',
          orange: '#ff6600',
          red: '#ff0040',
        },
        // Cyber colors
        cyber: {
          dark: '#0a0a0f',
          darker: '#050508',
          card: '#0d0d14',
          border: '#1a1a2e',
          glow: '#00f5ff',
        },
      },
      fontFamily: {
        cyber: ['Orbitron', 'Rajdhani', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'neon-blue': '0 0 5px #00f5ff, 0 0 10px #00f5ff, 0 0 20px #00f5ff, 0 0 40px #00f5ff',
        'neon-purple': '0 0 5px #bf00ff, 0 0 10px #bf00ff, 0 0 20px #bf00ff, 0 0 40px #bf00ff',
        'neon-green': '0 0 5px #00ff88, 0 0 10px #00ff88, 0 0 20px #00ff88, 0 0 40px #00ff88',
        'neon-pink': '0 0 5px #ff00ff, 0 0 10px #ff00ff, 0 0 20px #ff00ff, 0 0 40px #ff00ff',
        'glow-sm': '0 0 10px rgba(0, 245, 255, 0.3)',
        'glow-md': '0 0 20px rgba(0, 245, 255, 0.4)',
        'glow-lg': '0 0 30px rgba(0, 245, 255, 0.5)',
        'card': '0 0 20px rgba(0, 245, 255, 0.1), 0 8px 32px rgba(0, 0, 0, 0.4)',
        'card-hover': '0 0 30px rgba(0, 245, 255, 0.2), 0 8px 32px rgba(0, 0, 0, 0.6)',
      },
      animation: {
        'pulse-neon': 'pulse-neon 2s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'scan': 'scan 4s linear infinite',
        'float': 'float 6s ease-in-out infinite',
        'gradient-x': 'gradient-x 3s ease infinite',
        'gradient-y': 'gradient-y 3s ease infinite',
        'gradient-xy': 'gradient-xy 4s ease infinite',
        'border-flow': 'border-flow 3s linear infinite',
        'text-shimmer': 'text-shimmer 3s linear infinite',
        'flicker': 'flicker 0.15s infinite',
        'data-stream': 'data-stream 20s linear infinite',
      },
      keyframes: {
        'pulse-neon': {
          '0%, 100%': {
            boxShadow: '0 0 5px #00f5ff, 0 0 10px #00f5ff, 0 0 20px #00f5ff',
            opacity: 1,
          },
          '50%': {
            boxShadow: '0 0 10px #00f5ff, 0 0 20px #00f5ff, 0 0 40px #00f5ff, 0 0 60px #00f5ff',
            opacity: 0.8,
          },
        },
        'glow': {
          '0%': {
            boxShadow: '0 0 5px rgba(0, 245, 255, 0.5), 0 0 10px rgba(0, 245, 255, 0.3)',
          },
          '100%': {
            boxShadow: '0 0 10px rgba(0, 245, 255, 0.8), 0 0 20px rgba(0, 245, 255, 0.5), 0 0 30px rgba(0, 245, 255, 0.3)',
          },
        },
        'scan': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'gradient-x': {
          '0%, 100%': {
            backgroundSize: '200% 200%',
            backgroundPosition: 'left center',
          },
          '50%': {
            backgroundSize: '200% 200%',
            backgroundPosition: 'right center',
          },
        },
        'gradient-y': {
          '0%, 100%': {
            backgroundSize: '400% 400%',
            backgroundPosition: 'center top',
          },
          '50%': {
            backgroundSize: '200% 200%',
            backgroundPosition: 'center center',
          },
        },
        'gradient-xy': {
          '0%, 100%': {
            backgroundSize: '400% 400%',
            backgroundPosition: 'left center',
          },
          '50%': {
            backgroundSize: '200% 200%',
            backgroundPosition: 'right center',
          },
        },
        'border-flow': {
          '0%': { backgroundPosition: '0% 50%' },
          '100%': { backgroundPosition: '200% 50%' },
        },
        'text-shimmer': {
          '0%': { backgroundPosition: '-200% center' },
          '100%': { backgroundPosition: '200% center' },
        },
        'flicker': {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.8 },
        },
        'data-stream': {
          '0%': { transform: 'translateY(0)' },
          '100%': { transform: 'translateY(-50%)' },
        },
      },
      backgroundImage: {
        'cyber-gradient': 'linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%)',
        'neon-gradient': 'linear-gradient(90deg, #00f5ff 0%, #bf00ff 50%, #00ff88 100%)',
        'card-gradient': 'linear-gradient(145deg, rgba(13, 13, 20, 0.9) 0%, rgba(26, 26, 46, 0.8) 100%)',
        'glass': 'linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%)',
        'grid-pattern': 'linear-gradient(rgba(0, 245, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 245, 255, 0.03) 1px, transparent 1px)',
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: 'none',
            'h1': {
              fontSize: '2.25rem',
              fontWeight: '700',
              marginTop: '2rem',
              marginBottom: '1rem',
              letterSpacing: '-0.025em',
              color: 'var(--tw-prose-headings)',
            },
            'h2': {
              fontSize: '1.75rem',
              fontWeight: '600',
              marginTop: '2.5rem',
              marginBottom: '1rem',
              letterSpacing: '-0.02em',
              paddingBottom: '0.5rem',
              borderBottom: '1px solid var(--tw-prose-borders)',
            },
            'h3': {
              fontSize: '1.375rem',
              fontWeight: '600',
              marginTop: '2rem',
              marginBottom: '0.75rem',
            },
            'h4': {
              fontSize: '1.125rem',
              fontWeight: '600',
              marginTop: '1.5rem',
              marginBottom: '0.5rem',
            },
            'p': {
              lineHeight: '1.75',
              marginBottom: '1.25rem',
            },
            'ul': {
              listStyleType: 'disc',
              paddingLeft: '1.5rem',
            },
            'ol': {
              listStyleType: 'decimal',
              paddingLeft: '1.5rem',
            },
            'li': {
              marginTop: '0.5rem',
              marginBottom: '0.5rem',
              paddingLeft: '0.25rem',
            },
            'li::marker': {
              color: 'var(--tw-prose-counters)',
            },
            'blockquote': {
              fontWeight: '500',
              fontStyle: 'italic',
              borderLeftWidth: '4px',
              borderLeftColor: 'var(--tw-prose-quote-borders)',
              backgroundColor: 'var(--tw-prose-quotes)',
              borderRadius: '0 0.5rem 0.5rem 0',
              paddingTop: '1rem',
              paddingBottom: '1rem',
              paddingLeft: '1.5rem',
              paddingRight: '1rem',
              margin: '1.5rem 0',
            },
            'code': {
              fontWeight: '500',
              backgroundColor: 'var(--tw-prose-code-bg)',
              borderRadius: '0.375rem',
              paddingTop: '0.25rem',
              paddingBottom: '0.25rem',
              paddingLeft: '0.375rem',
              paddingRight: '0.375rem',
            },
            'code::before': {
              content: '""',
            },
            'code::after': {
              content: '""',
            },
            'pre': {
              backgroundColor: '#1e293b',
              borderRadius: '0.75rem',
              padding: '1.25rem',
              overflowX: 'auto',
              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
            },
            'pre code': {
              backgroundColor: 'transparent',
              fontWeight: '400',
              fontSize: '0.875rem',
              lineHeight: '1.7',
            },
            'table': {
              width: '100%',
              borderCollapse: 'collapse',
              borderRadius: '0.75rem',
              overflow: 'hidden',
              boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
              margin: '1.5rem 0',
            },
            'thead': {
              borderBottomWidth: '2px',
            },
            'thead th': {
              fontWeight: '600',
              textAlign: 'left',
              backgroundColor: 'var(--tw-prose-th-borders)',
              padding: '0.875rem 1rem',
            },
            'tbody tr': {
              borderBottomWidth: '1px',
              transition: 'background-color 150ms',
            },
            'tbody tr:nth-child(odd)': {
              backgroundColor: 'var(--tw-prose-td-borders)',
            },
            'tbody tr:hover': {
              backgroundColor: 'var(--tw-prose-td-hover)',
            },
            'tbody td': {
              padding: '0.875rem 1rem',
            },
            'a': {
              textDecoration: 'none',
              fontWeight: '500',
              borderBottomWidth: '1px',
              borderBottomStyle: 'dashed',
              transition: 'all 150ms',
            },
            'a:hover': {
              borderBottomStyle: 'solid',
            },
            'hr': {
              marginTop: '2rem',
              marginBottom: '2rem',
              opacity: '0.5',
            },
            'img': {
              borderRadius: '0.75rem',
              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
              marginTop: '1.5rem',
              marginBottom: '1.5rem',
            },
            'strong': {
              fontWeight: '600',
            },
          },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
