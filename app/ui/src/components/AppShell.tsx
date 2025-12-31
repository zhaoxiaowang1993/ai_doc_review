import {
  Button,
  Input,
  makeStyles,
  mergeClasses,
  tokens,
} from '@fluentui/react-components'
import {
  DocumentBulletListRegular,
  SearchRegular,
  ShieldCheckmarkRegular,
  WeatherMoonRegular,
  WeatherSunnyRegular,
} from '@fluentui/react-icons'
import { PropsWithChildren } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import type { ThemeMode } from '../theme'

type AppShellProps = PropsWithChildren<{
  mode: ThemeMode
  onToggleMode: () => void
}>

const useStyles = makeStyles({
  shell: {
    minHeight: '100vh',
    color: tokens.colorNeutralForeground1,
  },
  layout: {
    display: 'grid',
    gridTemplateColumns: '260px 1fr',
    minHeight: '100vh',
  },
  // ========== SIDEBAR ==========
  nav: {
    padding: '20px 16px',
    borderRight: `1px solid ${tokens.colorNeutralStroke2}`,
    backdropFilter: 'blur(12px)',
    backgroundColor: tokens.colorNeutralBackground2,
  },
  // ========== BRAND ==========
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '14px 12px',
    borderRadius: '12px',
    backgroundColor: tokens.colorBrandBackground2,
    border: `1px solid ${tokens.colorBrandStroke2}`,
    marginBottom: '20px',
  },
  brandIcon: {
    width: '40px',
    height: '40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '10px',
    backgroundColor: tokens.colorBrandBackground,
    color: tokens.colorNeutralForegroundOnBrand,
    fontSize: '20px',
  },
  brandInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  statusRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: tokens.colorPaletteGreenBackground3,
    boxShadow: `0 0 6px ${tokens.colorPaletteGreenBackground3}`,
  },
  brandTitle: {
    fontSize: '14px',
    fontWeight: 700,
    color: tokens.colorBrandForeground1,
  },
  brandSub: {
    fontSize: '11px',
    color: tokens.colorNeutralForeground3,
  },
  // ========== NAV ITEMS ==========
  navSectionTitle: {
    fontSize: '11px',
    fontWeight: 600,
    color: tokens.colorNeutralForeground3,
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
    margin: '16px 12px 8px',
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px 12px',
    borderRadius: '8px',
    textDecoration: 'none',
    color: tokens.colorNeutralForeground2,
    border: '1px solid transparent',
    transitionProperty: 'all',
    transitionDuration: '150ms',
    '&:hover': {
      backgroundColor: tokens.colorSubtleBackgroundHover,
      color: tokens.colorNeutralForeground1,
    },
  },
  navItemActive: {
    backgroundColor: tokens.colorBrandBackground2,
    borderTopColor: tokens.colorBrandStroke1,
    borderRightColor: tokens.colorBrandStroke1,
    borderBottomColor: tokens.colorBrandStroke1,
    borderLeftColor: tokens.colorBrandStroke1,
    color: tokens.colorNeutralForeground1,
    fontWeight: 500,
    '&::before': {
      content: '""',
      position: 'absolute',
      left: 0,
      top: '50%',
      transform: 'translateY(-50%)',
      width: '3px',
      height: '20px',
      borderRadius: '0 2px 2px 0',
      backgroundColor: tokens.colorBrandBackground,
    },
  },
  navItemIcon: {
    color: tokens.colorBrandForeground1,
    fontSize: '18px',
  },
  // ========== CONTENT ==========
  content: {
    display: 'grid',
    gridTemplateRows: '56px 1fr',
    minWidth: 0,
  },
  // ========== TOP BAR ==========
  topbar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 20px',
    borderBottom: `1px solid ${tokens.colorNeutralStroke2}`,
    backgroundColor: tokens.colorNeutralBackground1,
    backdropFilter: 'blur(12px)',
  },
  titleSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  backButton: {
    minWidth: 'auto',
  },
  pageTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: tokens.colorBrandForeground1,
  },
  breadcrumbs: {
    fontSize: '12px',
    color: tokens.colorNeutralForeground3,
  },
  // ========== ACTIONS ==========
  actions: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
  },
  search: {
    width: '280px',
    maxWidth: '30vw',
  },
  // ========== PAGE ==========
  page: {
    padding: '20px',
    minWidth: 0,
    overflowY: 'auto',
  },
})

function NavItem({
  to,
  label,
  icon,
}: {
  to: string
  label: string
  icon: React.ReactNode
}) {
  const classes = useStyles()
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        mergeClasses(classes.navItem, isActive && classes.navItemActive)
      }
      style={{ position: 'relative' }}
    >
      <span className={classes.navItemIcon}>{icon}</span>
      <span>{label}</span>
    </NavLink>
  )
}

export function AppShell({ mode, onToggleMode, children }: AppShellProps) {
  const classes = useStyles()
  const location = useLocation()
  const navigate = useNavigate()

  const pageTitle = location.pathname === '/review' ? '智能审阅' : '文档库'

  return (
    <div className={classes.shell}>
      <div className={classes.layout}>
        <aside className={classes.nav}>
          <div className={classes.brand}>
            <div className={classes.brandIcon}>
              <ShieldCheckmarkRegular />
            </div>
            <div className={classes.brandInfo}>
              <div className={classes.statusRow}>
                <span className={classes.statusDot} />
                <span className={classes.brandTitle}>AI 文档审核</span>
              </div>
              <span className={classes.brandSub}>智能审阅 · 风险识别</span>
            </div>
          </div>

          <div className={classes.navSectionTitle}>工作台</div>
          <NavItem to="/" label="文档库" icon={<DocumentBulletListRegular />} />
        </aside>

        <div className={classes.content}>
          <header className={classes.topbar}>
            <div className={classes.titleSection}>
              {location.pathname !== '/' && (
                <Button
                  appearance="subtle"
                  size="small"
                  className={classes.backButton}
                  onClick={() => navigate(-1)}
                >
                  ← 返回
                </Button>
              )}
              <span className={classes.pageTitle}>{pageTitle}</span>
              <span className={classes.breadcrumbs}>/ 合规审阅中心</span>
            </div>
            <div className={classes.actions}>
              <Input
                className={classes.search}
                size="small"
                contentBefore={<SearchRegular />}
                placeholder="搜索文档、问题…"
              />
              <Button appearance="subtle" size="small" onClick={onToggleMode}>
                {mode === 'dark' ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <WeatherSunnyRegular />
                    浅色
                  </span>
                ) : (
                  <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <WeatherMoonRegular />
                    深色
                  </span>
                )}
              </Button>
            </div>
          </header>
          <main className={classes.page}>{children}</main>
        </div>
      </div>
    </div>
  )
}
