import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import { MapContainer, ImageOverlay, TileLayer } from 'react-leaflet'
import { useSummaryData } from '../api/hooks'
import MapResizer from '../components/MapResizer'

function StatCard({ icon, iconColor, bgColor, label, value, badge, badgeColor }) {
  return (
    <div className="glass p-5 rounded-2xl flex flex-col justify-between group hover:border-primary/50 transition-all shadow-sm">
      <div className="flex justify-between items-start mb-4">
        <div className={`${bgColor} p-2 rounded-lg`}>
          <span className={`material-symbols-outlined ${iconColor}`}>{icon}</span>
        </div>
        {badge && (
          <span className={`text-xs font-bold flex items-center px-2 py-1 rounded-full ${badgeColor}`}>{badge}</span>
        )}
      </div>
      <div>
        <p className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">{label}</p>
        <p className="text-3xl font-bold text-slate-900">{value}</p>
      </div>
    </div>
  )
}

function Skeleton() {
  return <div className="animate-pulse h-9 w-24 bg-slate-200 rounded" />
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [activeLayer, setActiveLayer] = useState('heatmap')
  const { data, loading, error } = useSummaryData()

  const CENTER = [17.4474, 78.3762]
  const lstBounds = data?.lst_bounds ?? [[17.0, 77.9], [17.9, 78.8]]
  const ndviBounds = data?.ndvi_bounds ?? [[17.0, 77.9], [17.9, 78.8]]

  // Values
  const avgC = loading ? null : data?.avg_temp_c
  const minC = loading ? null : data?.min_temp_c
  const maxC = loading ? null : data?.max_temp_c
  const canopy = loading ? null : data?.canopy_pct
  const exposed = loading ? null : data?.exposed_pct
  const shade = loading ? null : data?.shade_pct

  return (
    <div className="bg-background-light font-display text-slate-700 min-h-screen overflow-x-hidden">
      <Navbar variant="floating" />

      <main className="pt-32 pb-12 px-6 lg:px-12 max-w-[1600px] mx-auto space-y-8">
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center gap-2">
            <span className="material-symbols-outlined">error</span>
            Backend error: {error}. Showing cached or default values.
          </div>
        )}

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <div className="glass p-5 rounded-2xl flex flex-col justify-between group hover:border-primary/50 transition-all shadow-sm">
            <div className="flex justify-between items-start mb-4">
              <div className="bg-primary/10 p-2 rounded-lg">
                <span className="material-symbols-outlined text-primary">thermostat</span>
              </div>
            </div>
            <div>
              <p className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">Avg Temperature</p>
              {loading ? <Skeleton /> : <p className="text-3xl font-bold text-slate-900">{avgC}°C</p>}
            </div>
          </div>

          <div className="glass p-5 rounded-2xl flex flex-col justify-between group hover:border-primary/50 transition-all shadow-sm">
            <div className="flex justify-between items-start mb-4">
              <div className="bg-amber-500/10 p-2 rounded-lg">
                <span className="material-symbols-outlined text-amber-500">wb_sunny</span>
              </div>
            </div>
            <div>
              <p className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">Max / Min Zone</p>
              {loading ? <Skeleton /> : <p className="text-3xl font-bold text-slate-900">{maxC}°C/ {minC}°C</p>}
            </div>
          </div>

          <div className="glass p-5 rounded-2xl flex flex-col justify-between group hover:border-primary/50 transition-all shadow-sm">
            <div className="flex justify-between items-start mb-4">
              <div className="bg-secondary/10 p-2 rounded-lg">
                <span className="material-symbols-outlined text-secondary">park</span>
              </div>
            </div>
            <div>
              <p className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">Tree Canopy</p>
              {loading ? <Skeleton /> : <p className="text-3xl font-bold text-slate-900">{canopy}%</p>}
            </div>
          </div>

          <div className="glass p-5 rounded-2xl flex flex-col justify-between group hover:border-primary/50 transition-all shadow-sm">
            <div className="flex justify-between items-start mb-4">
              <div className="bg-rose-500/10 p-2 rounded-lg">
                <span className="material-symbols-outlined text-rose-500">grid_guides</span>
              </div>
            </div>
            <div>
              <p className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">Exposed Area</p>
              {loading ? <Skeleton /> : <p className="text-3xl font-bold text-slate-900">{exposed}%</p>}
            </div>
          </div>

          <div className="glass p-5 rounded-2xl flex flex-col justify-between group hover:border-primary/50 transition-all shadow-sm">
            <div className="flex justify-between items-start mb-4">
              <div className="bg-sky-500/10 p-2 rounded-lg">
                <span className="material-symbols-outlined text-sky-500">umbrella</span>
              </div>
            </div>
            <div>
              <p className="text-slate-500 text-xs font-medium uppercase tracking-wider mb-1">Shade Coverage</p>
              {loading ? <Skeleton /> : <p className="text-3xl font-bold text-slate-900">{shade}%</p>}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            <div className="glass p-6 rounded-2xl shadow-sm">
              <h3 className="text-slate-900 font-bold mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-sm">layers</span>
                Map Toggles
              </h3>
              <div className="space-y-3">
                {[
                  { key: 'heatmap', icon: 'local_fire_department', label: 'Heatmap' },
                  { key: 'canopy', icon: 'forest', label: 'Tree Canopy' },
                  { key: 'both', icon: 'stacked_line_chart', label: 'Combined View' },
                ].map(({ key, icon, label }) => (
                  <button
                    key={key}
                    onClick={() => setActiveLayer(key)}
                    className={`w-full flex items-center justify-between p-3 rounded-xl text-sm font-semibold transition-all border ${activeLayer === key
                      ? 'bg-primary text-white border-primary'
                      : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                      }`}
                  >
                    <span className="flex items-center gap-3">
                      <span className="material-symbols-outlined text-sm">{icon}</span>
                      {label}
                    </span>
                    {activeLayer === key && <span className="material-symbols-outlined text-xs">check_circle</span>}
                  </button>
                ))}
              </div>
            </div>

            <div className="glass p-6 rounded-2xl shadow-sm">
              <h3 className="text-slate-900 font-bold mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-sm">rocket_launch</span>
                Quick Actions
              </h3>
              <div className="space-y-3">
                {[
                  { label: 'Heatmap Analysis', desc: 'Detailed urban heat data', path: '/heatmap' },
                  { label: 'Canopy Strategy', desc: 'NDVI breakdown by zone', path: '/canopy' },
                  { label: 'Open Router', desc: 'Plan a cool delivery route', path: '/router' },
                ].map(({ label, desc, path }) => (
                  <button key={label} onClick={() => navigate(path)} className="w-full bg-slate-50 hover:bg-primary hover:text-white transition-all p-4 rounded-xl text-left border border-slate-100 group">
                    <p className="font-bold text-sm text-slate-900 group-hover:text-white">{label}</p>
                    <p className="text-xs text-slate-500 group-hover:text-white/80">{desc}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Map Container */}
          <div className="lg:col-span-3 relative">
            <div className="glass rounded-3xl overflow-hidden h-[600px] border border-primary/10 relative shadow-inner">
              <MapContainer
                center={CENTER}
                zoom={11}
                style={{ width: '100%', height: '100%', zIndex: 0 }}
                zoomControl={true}
                attributionControl={false}
              >
                <MapResizer />
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {(activeLayer === 'heatmap' || activeLayer === 'both') && data?.lst_image_url && (
                  <ImageOverlay url={data.lst_image_url} bounds={lstBounds} opacity={0.65} />
                )}
                {(activeLayer === 'canopy' || activeLayer === 'both') && data?.ndvi_image_url && (
                  <ImageOverlay url={data.ndvi_image_url} bounds={ndviBounds} opacity={0.60} />
                )}
              </MapContainer>

              {/* Loading overlay */}
              {loading && (
                <div className="absolute inset-0 bg-white/40 z-[400] flex items-center justify-center">
                  <div className="bg-white rounded-xl shadow-lg p-4 flex items-center gap-3">
                    <span className="material-symbols-outlined text-primary animate-spin">refresh</span>
                    <span className="text-sm font-medium text-slate-700">Loading satellite data…</span>
                  </div>
                </div>
              )}

              {/* Legend */}
              <div className="absolute bottom-6 left-6 z-[400] glass p-4 rounded-2xl w-64 border border-white/40 shadow-xl">
                <p className="text-[10px] font-bold text-slate-900 mb-3 flex items-center justify-between tracking-widest uppercase">
                  {activeLayer === 'canopy' ? 'NDVI Density' : 'Heat Intensity'}
                  <span className="material-symbols-outlined text-sm text-slate-400">info</span>
                </p>
                <div className="h-2 w-full rounded-full mb-2"
                  style={{
                    background: activeLayer === 'canopy'
                      ? 'linear-gradient(to right, #92400e, #eab308, #15803d)'
                      : 'linear-gradient(to right, #15803d, #eab308, #b91c1c)'
                  }}
                />
                <div className="flex justify-between text-[10px] text-slate-500 font-bold">
                  {activeLayer === 'canopy'
                    ? <><span>Sparse</span><span className="text-secondary">Dense</span></>
                    : <><span>{data?.min_temp_c ?? '--'}°C</span><span className="text-secondary">OPTIMAL</span><span>{data?.max_temp_c ?? '--'}°C</span></>
                  }
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      <footer className="max-w-7xl mx-auto px-12 py-8 flex flex-col md:flex-row justify-between items-center text-slate-400 text-sm border-t border-slate-200">
        <div className="flex items-center gap-2 mb-4 md:mb-0">
          <span className="material-symbols-outlined text-primary/60 text-lg">verified</span>
          <span className="font-medium">
            {loading ? 'Loading data…' : error ? 'Backend offline' : 'All systems operational'}
          </span>
        </div>
        <div className="flex items-center gap-6">
        </div>
      </footer>
    </div>
  )
}
