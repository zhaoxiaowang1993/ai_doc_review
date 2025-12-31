import { BrandVariants, Theme, createDarkTheme, createLightTheme } from '@fluentui/react-components'

export type ThemeMode = 'dark' | 'light'

// 专业科技感配色：靛蓝为主色调
const brand: BrandVariants = {
  10: '#050a18',
  20: '#0a1428',
  30: '#0f1e3c',
  40: '#142850',
  50: '#1a3366',
  60: '#1f3d7a',
  70: '#2952a3',
  80: '#3366cc',  // Primary
  90: '#4d7dd9',
  100: '#6699e6',
  110: '#80b3f0',
  120: '#99c2f5',
  130: '#b3d1f7',
  140: '#cce0fa',
  150: '#e6f0fc',
  160: '#f5f9ff',
}

// 科技感强调色 - 深色/浅色模式共用
export const accentColors = {
  // 主强调色
  primary: '#3366cc',
  primaryLight: '#4d7dd9',
  primaryDark: '#2952a3',
  // 功能色
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#06b6d4',
  // 深色模式专用
  dark: {
    bg: '#0f172a',
    bgElevated: '#1e293b',
    bgCard: 'rgba(30, 41, 59, 0.8)',
    border: 'rgba(148, 163, 184, 0.15)',
    borderHover: 'rgba(148, 163, 184, 0.3)',
    text: '#f1f5f9',
    textMuted: '#94a3b8',
  },
  // 浅色模式专用
  light: {
    bg: '#f8fafc',
    bgElevated: '#ffffff',
    bgCard: 'rgba(255, 255, 255, 0.9)',
    border: 'rgba(15, 23, 42, 0.1)',
    borderHover: 'rgba(15, 23, 42, 0.2)',
    text: '#0f172a',
    textMuted: '#64748b',
  },
}

export function getAppTheme(mode: ThemeMode): Theme {
  const base = mode === 'dark' ? createDarkTheme(brand) : createLightTheme(brand)

  return {
    ...base,
    fontFamilyBase:
      '"Inter", "SF Pro Display", "Segoe UI Variable", system-ui, -apple-system, sans-serif',
    fontFamilyMonospace: '"JetBrains Mono", "Fira Code", "SF Mono", monospace',
  }
}
