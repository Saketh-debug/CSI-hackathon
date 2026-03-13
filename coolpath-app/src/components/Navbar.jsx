import { NavLink, useNavigate, useLocation } from 'react-router-dom'

const navLinks = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/heatmap', label: 'Temperature Map' },
  { to: '/canopy', label: 'Tree Canopy' },
  { to: '/router', label: 'CoolPath Router' },
  { to: '/messaging', label: 'Messaging' },
]

export default function Navbar({ variant = 'default' }) {
  const navigate = useNavigate()
  const location = useLocation()
  const isHome = location.pathname === '/'

  if (variant === 'floating') {
    return (
      <nav className="fixed top-6 left-1/2 -translate-x-1/2 z-50 w-[95%] max-w-7xl">
        <div className="glass-nav rounded-2xl px-8 py-4 flex items-center justify-between shadow-xl shadow-slate-200/50">
          {/* Logo */}
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => navigate('/')}
          >
            <div className="bg-primary/10 p-2 rounded-lg">
              <span className="material-symbols-outlined text-primary text-2xl">ac_unit</span>
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 uppercase italic">CoolPath</h1>
          </div>
          {/* Center Links */}
          <div className="hidden lg:flex items-center gap-6">
            {navLinks.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  isActive
                    ? 'text-primary font-semibold text-sm transition-colors'
                    : 'text-slate-500 hover:text-primary text-sm font-medium transition-colors'
                }
              >
                {label}
              </NavLink>
            ))}
          </div>
          {/* Right */}

        </div>
      </nav>
    )
  }

  // Default sticky-header variant (used by most pages)
  return (
    <header className="flex items-center justify-between whitespace-nowrap border-b border-slate-200 bg-white/70 backdrop-blur-md px-6 py-3 sticky top-0 z-50 lg:px-10">
      <div className="flex items-center gap-8">
        <div
          className="flex items-center gap-3 cursor-pointer"
          onClick={() => navigate('/')}
        >
          <div className="size-9 bg-primary/10 rounded-lg flex items-center justify-center">
            <span className="material-symbols-outlined text-primary font-bold">thermostat</span>
          </div>
          <h2 className="text-slate-900 text-xl font-bold leading-tight tracking-tight">CoolPath</h2>
        </div>
      </div>
      <div className="flex flex-1 justify-end gap-4 lg:gap-8 items-center">
        <nav className="hidden lg:flex items-center gap-6">
          {navLinks.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                isActive
                  ? 'text-primary text-sm font-bold relative py-1 after:absolute after:bottom-0 after:left-0 after:w-full after:h-0.5 after:bg-primary'
                  : 'text-slate-600 hover:text-primary text-sm font-semibold transition-colors'
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        {isHome && (
          <button
            className="rounded-lg bg-primary px-5 py-2.5 text-sm font-bold text-white transition-all hover:bg-primary/90"
            onClick={() => navigate('/dashboard')}
          >
            Sign In
          </button>
        )}
      </div>
    </header>
  )
}
