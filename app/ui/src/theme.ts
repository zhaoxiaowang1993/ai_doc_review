import { BrandVariants, Theme, createLightTheme } from '@fluentui/react-components'

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
}

export function getAppTheme(): Theme {
  const base = createLightTheme(brand)
  return {
    ...base,
    fontFamilyBase:
      '"Inter", "SF Pro Display", "Segoe UI Variable", system-ui, -apple-system, sans-serif',
    fontFamilyMonospace: '"JetBrains Mono", "Fira Code", "SF Mono", monospace',
  }
}
