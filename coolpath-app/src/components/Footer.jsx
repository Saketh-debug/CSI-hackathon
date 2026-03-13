import { useNavigate } from 'react-router-dom'

export default function Footer() {
  const navigate = useNavigate()
  return (
    <footer className="border-t border-slate-100 bg-white py-12 px-6 lg:px-20">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col items-center justify-between gap-8 md:flex-row">
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => navigate('/')}
          >
            <div className="flex h-8 w-8 items-center justify-center rounded bg-primary/10 text-primary">
              <span className="material-symbols-outlined text-lg">thermostat</span>
            </div>
            <span className="text-lg font-bold text-slate-900">CoolPath</span>
          </div>
          <div className="flex flex-wrap justify-center gap-8">
            <a className="text-sm font-medium text-slate-500 hover:text-primary transition-colors" href="#">Privacy Policy</a>
            <a className="text-sm font-medium text-slate-500 hover:text-primary transition-colors" href="#">Terms of Service</a>
            <a className="text-sm font-medium text-slate-500 hover:text-primary transition-colors" href="#">API Keys</a>
            <a className="text-sm font-medium text-slate-500 hover:text-primary transition-colors" href="#">Contact Support</a>
          </div>
        </div>
        <div className="mt-12 text-center text-xs text-slate-400">
          © 2024 CoolPath Thermal Intelligence. Built for a resilient future.
        </div>
      </div>
    </footer>
  )
}
