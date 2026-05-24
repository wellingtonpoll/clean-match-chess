import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      obsidiana: '#0B0B0D',
      'obsidiana-2': '#131316',
      nucleo: '#1E1E22',
      aco: '#2A2A2E',
      grafite: '#4A4A50',
      pulso: '#7A7A80',
      metal: '#B8B5AE',
      osso: '#F2EFE8',
      'osso-2': '#E8E4DA',
      papel: '#FAF7F1',
      sangue: '#8B0F14',
      'sangue-luz': '#B81820',
      brasa: '#C9201F',
      white: '#FFFFFF',
      black: '#000000',
    },
    fontFamily: {
      serif: ['Instrument Serif', 'Georgia', 'serif'],
      sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
      mono: ['JetBrains Mono', 'Menlo', 'monospace'],
    },
    borderRadius: {
      DEFAULT: '0',
      none: '0',
    },
    extend: {
      maxWidth: {
        '4xl': '56rem',
        '5xl': '64rem',
      },
    },
  },
  plugins: [],
}

export default config
