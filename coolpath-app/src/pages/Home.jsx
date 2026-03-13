import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-slate-50 text-slate-900">
      {/* Standardized Navigation */}
      <header className="fixed top-0 z-50 w-full nav-glass px-6 py-4 lg:px-20">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div
            className="flex items-center gap-3 cursor-pointer"
            onClick={() => navigate('/')}
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white shadow-lg shadow-primary/20">
              <span className="material-symbols-outlined font-bold">thermostat</span>
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900">Verdex</span>
          </div>
          <nav className="hidden md:flex items-center gap-8">
            <span
              className="text-sm font-semibold text-slate-600 hover:text-primary transition-colors cursor-pointer"
              onClick={() => navigate('/dashboard')}
            >Dashboard</span>
            <span
              className="text-sm font-semibold text-slate-600 hover:text-primary transition-colors cursor-pointer"
              onClick={() => navigate('/heatmap')}
            >Temperature Map</span>
            <span
              className="text-sm font-semibold text-slate-600 hover:text-primary transition-colors cursor-pointer"
              onClick={() => navigate('/canopy')}
            >Tree Canopy</span>
            <span
              className="text-sm font-semibold text-slate-600 hover:text-primary transition-colors cursor-pointer"
              onClick={() => navigate('/router')}
            >CoolPath Router</span>
            <span
              className="text-sm font-semibold text-slate-600 hover:text-primary transition-colors cursor-pointer"
              onClick={() => navigate('/messaging')}
            >Messaging</span>
          </nav>

        </div>
      </header>

      <main className="flex-grow pt-24">
        {/* Hero Section */}
        <section className="relative flex min-h-[85vh] items-center justify-center px-6 py-20 lg:px-20">
          <div className="absolute inset-0 -z-10 overflow-hidden">
            <div
              className="absolute inset-0 bg-cover bg-center opacity-5 grayscale"
              style={{ backgroundImage: "url('https://images.unsplash.com/photo-1449824913935-59a10b8d2000?auto=format&fit=crop&q=80&w=1920')" }}
            ></div>
            <div className="absolute inset-0 bg-gradient-to-b from-slate-50/60 via-slate-50/90 to-slate-50"></div>
            <div className="absolute top-1/4 left-1/4 h-96 w-96 rounded-full bg-primary/5 blur-[120px]"></div>
            <div className="absolute bottom-1/4 right-1/4 h-96 w-96 rounded-full bg-secondary/5 blur-[120px]"></div>
          </div>
          <div className="mx-auto max-w-4xl text-center">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-4 py-1.5 text-xs font-semibold uppercase tracking-wider text-primary">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-primary"></span>
              </span>
              Live Thermal Intelligence
            </div>
            <h1 className="mb-8 text-5xl font-black leading-[1.1] tracking-tight text-slate-900 md:text-7xl lg:text-8xl">
              Verdex – <span className="text-primary">Thermal</span> Intelligence Platform
            </h1>
            <p className="mx-auto mb-12 max-w-2xl text-lg leading-relaxed text-slate-600 md:text-xl">
              Extreme localized urban heat creates severe health risks for outdoor workers and degrades city livability. Verdex provides hyper-local thermal intelligence that helps businesses protect gig workers and city planners identify where cooling infrastructure and tree cover are needed most.
            </p>
            <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
              <button
                className="group relative flex h-14 min-w-[220px] items-center justify-center overflow-hidden rounded-xl bg-primary px-8 text-lg font-bold text-white transition-all hover:shadow-[0_0_30px_rgba(13,162,231,0.4)]"
                onClick={() => navigate('/dashboard')}
              >
                Enter Dashboard
                <span className="material-symbols-outlined ml-2 transition-transform group-hover:translate-x-1">arrow_forward</span>
              </button>
              <button
                className="h-14 min-w-[220px] rounded-xl border border-slate-200 bg-white px-8 text-lg font-bold text-slate-700 shadow-sm transition-all hover:bg-slate-50"
                onClick={() => navigate('/heatmap')}
              >
                View Live Map
              </button>
            </div>
          </div>
        </section>

        {/* Feature Cards Section */}
        <section className="relative z-10 mx-auto max-w-7xl px-6 py-24 lg:px-20">
          <div className="mb-16 flex flex-col items-start gap-4">
            <h2 className="text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">Platform Solutions</h2>
            <div className="h-1.5 w-24 rounded-full bg-secondary"></div>
            <p className="max-w-xl text-slate-600">Advanced monitoring and analytical tools designed for climate resilience and worker safety.</p>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {/* Card 1 */}
            <div className="glass-card group flex flex-col rounded-2xl p-8 transition-all hover:-translate-y-2 hover:border-primary/40 hover:shadow-2xl hover:shadow-primary/5">
              <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 text-primary group-hover:bg-primary group-hover:text-white transition-colors">
                <span className="material-symbols-outlined text-3xl">location_on</span>
              </div>
              <h3 className="mb-4 text-xl font-bold text-slate-900">Hyper-Local Temperature Mapping</h3>
              <p className="text-slate-600 leading-relaxed">
                Real-time monitoring of urban heat islands at street level with meter-level precision using proprietary sensor fusion.
              </p>
              <div className="mt-8 pt-6 border-t border-slate-100">
                <button
                  className="inline-flex items-center text-sm font-bold text-primary hover:underline"
                  onClick={() => navigate('/heatmap')}
                >
                  Learn more
                  <span className="material-symbols-outlined text-sm ml-1">chevron_right</span>
                </button>
              </div>
            </div>
            {/* Card 2 */}
            <div className="glass-card group flex flex-col rounded-2xl p-8 transition-all hover:-translate-y-2 hover:border-secondary/40 hover:shadow-2xl hover:shadow-secondary/5">
              <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-xl bg-secondary/10 text-secondary group-hover:bg-secondary group-hover:text-white transition-colors">
                <span className="material-symbols-outlined text-3xl">park</span>
              </div>
              <h3 className="mb-4 text-xl font-bold text-slate-900">Tree Canopy &amp; Shade Analysis</h3>
              <p className="text-slate-600 leading-relaxed">
                Identify critical gaps in cooling infrastructure and optimize tree placement based on solar trajectory and heat intensity.
              </p>
              <div className="mt-8 pt-6 border-t border-slate-100">
                <button
                  className="inline-flex items-center text-sm font-bold text-secondary hover:underline"
                  onClick={() => navigate('/canopy')}
                >
                  Explore shade data
                  <span className="material-symbols-outlined text-sm ml-1">chevron_right</span>
                </button>
              </div>
            </div>
            {/* Card 3 */}
            <div className="glass-card group flex flex-col rounded-2xl p-8 transition-all hover:-translate-y-2 hover:border-primary/40 hover:shadow-2xl hover:shadow-primary/5">
              <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 text-primary group-hover:bg-primary group-hover:text-white transition-colors">
                <span className="material-symbols-outlined text-3xl">route</span>
              </div>
              <h3 className="mb-4 text-xl font-bold text-slate-900">Climate-Aware Smart Routing</h3>
              <p className="text-slate-600 leading-relaxed">
                Protect outdoor and gig workers with heat-safe navigation paths that prioritize shaded streets and cooling hubs.
              </p>
              <div className="mt-8 pt-6 border-t border-slate-100">
                <button
                  className="inline-flex items-center text-sm font-bold text-primary hover:underline"
                  onClick={() => navigate('/router')}
                >
                  API Documentation
                  <span className="material-symbols-outlined text-sm ml-1">chevron_right</span>
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* Map Visual Section */}
        <section className="mx-auto max-w-7xl px-6 py-24 lg:px-20">
          <div className="glass-card relative overflow-hidden rounded-3xl p-1 md:p-3 shadow-xl">
            <div className="aspect-video w-full overflow-hidden rounded-2xl bg-slate-100 shadow-inner relative">
              <img
                className="h-full w-full object-cover opacity-80"
                alt="Digital city heat map visualization"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBK3uH7fnvYWsz7RvKRstmr4CjJf64OyQadjDhOXSQyb78ib4WdZC-gMztqcWbKeRNbcxPbMRDUF8A5iQEPwNMyYMm5lu7WuA5_u_a5iVN7_PZc_J5M4zPlu7m-_CSh9ZP9TauZUHiIwvdiSTGoEDaydKEDsQTMTXmQnoxQ9Ffy8577YMgDuSIyIritwK-C5ByRvmB-pPFn7VaTkyFMpnyDaj7_uiDTRjSlbFRuipUjhB4MCrc5Psg42_iM5O-cnB0gXccz-VTZIidk"
              />
              <div className="absolute inset-0 bg-gradient-to-tr from-primary/10 to-transparent pointer-events-none"></div>
              <div className="absolute bottom-10 left-10 max-w-xs rounded-xl bg-white/95 p-6 shadow-xl backdrop-blur-md border border-slate-100">
                <h4 className="mb-2 font-bold text-slate-900">Live Insights</h4>
                <div className="flex items-center gap-2 text-primary">
                  <span className="material-symbols-outlined text-sm">trending_up</span>
                  <span className="text-xs font-semibold uppercase">Heat Index +4.2°C Above Avg</span>
                </div>
                <div className="mt-4 flex gap-4">
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase text-slate-400">Shade Cover</span>
                    <span className="font-bold text-slate-900">24%</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] uppercase text-slate-400">Risk Level</span>
                    <span className="font-bold text-red-500">High</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="mx-auto max-w-4xl px-6 py-32 text-center">
          <h2 className="mb-8 text-4xl font-bold tracking-tight text-slate-900 md:text-5xl">Ready to build a cooler, safer city?</h2>
          <p className="mb-12 text-lg text-slate-600">Join the planners and fleet operators using thermal intelligence to save lives.</p>
          <div className="flex justify-center">
            <button
              className="flex h-16 min-w-[280px] items-center justify-center rounded-xl bg-primary text-xl font-black text-white shadow-xl shadow-primary/30 transition-all hover:scale-105 hover:bg-primary/90"
              onClick={() => navigate('/dashboard')}
            >
              Enter Dashboard
              <span className="material-symbols-outlined ml-3 text-2xl">dashboard</span>
            </button>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  )
}
