import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { PAGES } from '../lib/pages'

export function SunMark({ size = 20, color = '#fff' }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden>
      <circle cx="16" cy="16" r="6.5" fill={color} />
      <g stroke={color} strokeWidth="2.5" strokeLinecap="round">
        <path d="M16 2v4M16 26v4M2 16h4M26 16h4M6.1 6.1l2.8 2.8M23.1 23.1l2.8 2.8M6.1 25.9l2.8-2.8M23.1 8.9l2.8-2.8" />
      </g>
    </svg>
  )
}

export default function Layout() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return (
    <div className="shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand" aria-label="SuryaCast home">
          <span className="brand-mark">
            <SunMark />
          </span>
          <span>
            <div className="brand-name">SURYA CAST</div>
            <div className="brand-tag">See Tomorrow's Sun.</div>
          </span>
        </NavLink>
        <nav className="nav" aria-label="Dashboard pages">
          <NavLink to="/" end>
            <span className="nav-num">◎</span>Overview
          </NavLink>
          {PAGES.map((p) => (
            <NavLink key={p.path} to={p.path}>
              <span className="nav-num">{p.num}</span>
              {p.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          Sahasranshu Technologies Pvt. Ltd.
          <br />
          Rodic InfraAI Innovation Challenge 2026
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
