import {
  Button,
  makeStyles,
  mergeClasses,
  tokens,
} from '@fluentui/react-components'
import {
  DocumentBulletListRegular,
  BookRegular,
  PanelLeftContractRegular,
  PanelLeftExpandRegular,
} from '@fluentui/react-icons'
import { PropsWithChildren, useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import logo from '../assets/landing/logo.svg'
import { getDocument } from '../services/api'

type AppShellProps = PropsWithChildren<{}>

const useStyles = makeStyles({
  shell: {
    minHeight: '100vh',
    color: tokens.colorNeutralForeground1,
  },
  layout: {
    display: 'grid',
    minHeight: '100vh',
  },
  // ========== SIDEBAR ==========
  nav: {
    padding: '20px 16px',
    borderRight: `1px solid ${tokens.colorNeutralStroke2}`,
    backdropFilter: 'blur(12px)',
    backgroundColor: tokens.colorNeutralBackground2,
    transitionProperty: 'padding',
    transitionDuration: '150ms',
  },
  navCollapsed: {
    padding: '20px 8px',
    backgroundColor: tokens.colorNeutralBackground1,
    backdropFilter: 'none',
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
    transitionProperty: 'padding',
    transitionDuration: '150ms',
  },
  brandCollapsed: {
    padding: 0,
    justifyContent: 'center',
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: 0,
    marginBottom: '12px',
  },
  brandIcon: {
    width: '40px',
    height: '40px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '10px',
    color: tokens.colorNeutralForegroundOnBrand,
    fontSize: '20px',
  },
  brandInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  brandInfoCollapsed: {
    display: 'none',
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
  navSectionTitleCollapsed: {
    display: 'none',
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
    position: 'relative',
    transitionProperty: 'all',
    transitionDuration: '150ms',
    '&:hover': {
      backgroundColor: tokens.colorSubtleBackgroundHover,
      color: tokens.colorNeutralForeground1,
    },
  },
  navItemCollapsed: {
    justifyContent: 'center',
    padding: '10px 8px',
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
  navItemLabelCollapsed: {
    display: 'none',
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
  breadcrumbLink: {
    minWidth: 'auto',
    paddingLeft: 0,
    paddingRight: 0,
    fontSize: '12px',
    color: tokens.colorNeutralForeground3,
    '&:hover': {
      color: tokens.colorNeutralForeground2,
      textDecorationLine: 'underline',
    },
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
  collapsed,
}: {
  to: string
  label: string
  icon: React.ReactNode
  collapsed: boolean
}) {
  const classes = useStyles()
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        mergeClasses(
          classes.navItem,
          collapsed && classes.navItemCollapsed,
          isActive && classes.navItemActive,
        )
      }
      aria-label={label}
    >
      <span className={classes.navItemIcon}>{icon}</span>
      <span className={collapsed ? classes.navItemLabelCollapsed : undefined}>{label}</span>
    </NavLink>
  )
}

export function AppShell({ children }: AppShellProps) {
  const classes = useStyles()
  const location = useLocation()
  const navigate = useNavigate()

  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const raw = localStorage.getItem('sidebarCollapsed')
    return raw === '1'
  })

  useEffect(() => {
    localStorage.setItem('sidebarCollapsed', sidebarCollapsed ? '1' : '0')
  }, [sidebarCollapsed])

  const pageTitle = useMemo(() => {
    if (location.pathname === '/rules') return '规则库'
    return '文档库'
  }, [location.pathname])

  const [reviewDocTitle, setReviewDocTitle] = useState<string>('未命名文书')

  useEffect(() => {
    if (location.pathname !== '/review') return
    const docId = new URLSearchParams(location.search).get('doc_id') ?? undefined
    if (!docId) {
      setReviewDocTitle('未命名文书')
      return
    }
    setReviewDocTitle('文档')
    ;(async () => {
      try {
        const doc = await getDocument(docId)
        const name = (doc.display_name || doc.original_filename || '文档').replace(/\.pdf$/i, '')
        setReviewDocTitle(name)
      } catch {
        setReviewDocTitle('文档')
      }
    })()
  }, [location.pathname, location.search])

  return (
    <div className={classes.shell}>
      <div
        className={classes.layout}
        style={{
          gridTemplateColumns: sidebarCollapsed ? '64px 1fr' : '260px 1fr',
          transition: 'grid-template-columns 150ms ease',
        }}
      >
        <aside
          className={mergeClasses(classes.nav, sidebarCollapsed && classes.navCollapsed)}
        >
          <div
            className={mergeClasses(
              classes.brand,
              sidebarCollapsed && classes.brandCollapsed,
            )}
          >
            <div className={classes.brandIcon}>
              <img src={logo} alt="Logo" style={{ width: '100%', height: '100%' }} />
            </div>
            <div
              className={mergeClasses(
                classes.brandInfo,
                sidebarCollapsed && classes.brandInfoCollapsed,
              )}
            >
              <div className={classes.statusRow}>
                <span className={classes.statusDot} />
                <span className={classes.brandTitle}>AI 文档审核</span>
              </div>
              <span className={classes.brandSub}>智能审阅 · 风险识别</span>
            </div>
          </div>

          <div
            className={mergeClasses(
              classes.navSectionTitle,
              sidebarCollapsed && classes.navSectionTitleCollapsed,
            )}
          >
            工作台
          </div>
          <NavItem
            to="/files"
            label="文档库"
            icon={<DocumentBulletListRegular />}
            collapsed={sidebarCollapsed}
          />
          <NavItem
            to="/rules"
            label="规则库"
            icon={<BookRegular />}
            collapsed={sidebarCollapsed}
          />
        </aside>

        <div className={classes.content}>
          <header className={classes.topbar}>
            <div className={classes.titleSection}>
              <Button
                appearance="subtle"
                size="small"
                className={classes.backButton}
                onClick={() => setSidebarCollapsed((v) => !v)}
                aria-label={sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'}
                icon={sidebarCollapsed ? <PanelLeftExpandRegular /> : <PanelLeftContractRegular />}
              />
              {location.pathname === '/review' ? (
                <>
                  <Button
                    appearance="transparent"
                    size="small"
                    className={classes.breadcrumbLink}
                    onClick={() => navigate('/files')}
                  >
                    文档库
                  </Button>
                  <span className={classes.breadcrumbs}>/</span>
                  <span className={classes.pageTitle}>{reviewDocTitle}</span>
                </>
              ) : (
                <>
                  <span className={classes.pageTitle}>{pageTitle}</span>
                  <span className={classes.breadcrumbs}>/ 合规审阅中心</span>
                </>
              )}
            </div>
          </header>
          <main className={classes.page}>{children}</main>
        </div>
      </div>
    </div>
  )
}
