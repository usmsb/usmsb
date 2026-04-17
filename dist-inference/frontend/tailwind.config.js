/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'cyber-dark': '#0a0a0f',
        'cyber-card': '#0d0d14',
        'cyber-border': '#1a1a2e',
        'neon-blue': '#00f5ff',
        'neon-purple': '#bf00ff',
        'neon-green': '#00ff88',
        'neon-pink': '#ff00ff',
        'neon-red': '#ff0044',
        'neon-yellow': '#ffd700',
        'text-primary': '#e0e0ff',
        'text-secondary': '#8888aa',
      },
      fontFamily: {
        orbitron: ['Orbitron', 'sans-serif'],
        rajdhani: ['Rajdhani', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'neon-blue': '0 0 10px #00f5ff, 0 0 20px #00f5ff40',
        'neon-purple': '0 0 10px #bf00ff, 0 0 20px #bf00ff40',
        'neon-green': '0 0 10px #00ff88, 0 0 20px #00ff8840',
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'scanline': 'scanline 8s linear infinite',
        'grid-scroll': 'grid-scroll 20s linear infinite',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        'scanline': {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        'grid-scroll': {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '0 50px' },
        },
      },
      backgroundImage: {
        'cyber-grid': `linear-gradient(rgba(0,245,255,0.03) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(0,245,255,0.03) 1px, transparent 1px)`,
      },
      backgroundSize: {
        'cyber-grid': '50px 50px',
      },
    },
  },
  plugins: [],
}
