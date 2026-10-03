import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { PAGES } from '../lib/pages'

export function LogoMark({ size = 40 }: { size?: number }) {
  return <img src={`${import.meta.env.BASE_URL}logo.png`} width={size} height={size} alt="" aria-hidden style={{ display: 'block' }} />
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
            <LogoMark />
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
          SuryaCast is a product of Sahasranshu Technologies Pvt. Ltd.
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
