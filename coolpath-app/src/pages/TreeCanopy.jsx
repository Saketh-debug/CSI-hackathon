import { useState } from 'react'
import Navbar from '../components/Navbar'
import { MapContainer, ImageOverlay, TileLayer } from 'react-leaflet'
import { useCanopyData } from '../api/hooks'
import MapResizer from '../components/MapResizer'

function Bar({ value, color }) {
  return (
    <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
      <div className={`${color} h-full rounded-full transition-all duration-700`} style={{ width: `${value}%` }} />
    </div>
  )
}

function StatSkeleton() {
  return <div className="animate-pulse h-8 w-20 bg-slate-200 rounded" />
}

export default function TreeCanopy() {
  const [mapStyle, setMapStyle] = useState('osm') // 'osm' | 'satellite'
  const { data, loading, error } = useCanopyData()

  const CENTER = [17.4474, 78.3762]
  const mapBounds = data?.bounds ?? [[17.0, 77.9], [17.9, 78.8]]

  const maxNdvi    = data?.max_ndvi    ?? '—'
  const densePct   = data?.dense_pct   ?? 0
  const moderatePct= data?.moderate_pct?? 0
  const sparsePct  = data?.sparse_pct  ?? 0

  return (
    <div className="relative flex h-auto min-h-screen w-full flex-col overflow-x-hidden bg-background-light font-display text-slate-900 antialiased">
      <Navbar />

      <div className="flex flex-1 flex-col h-full overflow-hidden">
        <main className="flex-1 flex flex-col min-h-0">
          {/* Header */}
          <div className="px-6 py-8 lg:px-10 border-b border-slate-200 bg-background-surface flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <nav className="flex items-center gap-2 text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-2">
                <span>HOME</span>
                <span className="material-symbols-outlined text-[10px]">arrow_forward_ios</span>
                <span className="text-primary">TREE CANOPY ANALYSIS</span>
              </nav>
              <h1 className="text-slate-900 text-3xl font-black leading-tight tracking-tight">Tree Canopy Analysis</h1>
              <p className="text-slate-500 text-sm mt-1">Satellite NDVI visualization for vegetation health and urban shade optimization.</p>
            </div>
            <div className="flex gap-3">
              <button className="flex items-center gap-2 bg-primary px-4 py-2 rounded-lg text-white text-sm font-bold shadow-lg shadow-primary/20 hover:brightness-110 transition-all">
                <span className="material-symbols-outlined text-lg">layers</span>
                NDVI Layer
              </button>
            </div>
          </div>

          {/* Dashboard Grid */}
          <div className="flex-1 overflow-y-auto p-6 lg:p-10">
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                ⚠️ Could not load canopy data: {error}
              </div>
            )}
            <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
              {/* Map Container */}
              <div className="xl:col-span-3 flex flex-col gap-6">
                <div className="relative w-full h-[500px] lg:h-[650px] rounded-2xl overflow-hidden border border-slate-200 shadow-xl">
                  {/* Leaflet Map with NDVI overlay */}
                  <MapContainer
                    center={CENTER}
                    zoom={11}
                    style={{ width: '100%', height: '100%', zIndex: 0 }}
                    zoomControl={true}
                    attributionControl={false}
                  >
                    <MapResizer />
                    {mapStyle === 'osm' ? (
                      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                    ) : (
                      <TileLayer
                        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                        attribution="Esri"
                      />
                    )}
                    {data?.image_url && (
                      <ImageOverlay
                        url={data.image_url}
                        bounds={mapBounds}
                        opacity={0.70}
                      />
                    )}
                  </MapContainer>

                  {/* Map Style Controls */}
                  <div className="absolute top-6 left-16 bg-white/90 backdrop-blur-md rounded-xl shadow-xl border border-slate-200 p-1.5 flex flex-col z-[400] gap-1">
                    <button
                      onClick={() => setMapStyle('osm')}
                      className={`p-2.5 rounded-lg flex items-center justify-center transition-all ${mapStyle === 'osm' ? 'bg-slate-200 text-slate-800' : 'hover:bg-slate-100 text-slate-500'}`}
                      title="Map View"
                    >
                      <span className="material-symbols-outlined">map</span>
                    </button>
                    <div className="h-[1px] bg-slate-100 mx-2 my-1" />
                    <button
                      onClick={() => setMapStyle('satellite')}
                      className={`p-2.5 rounded-lg flex items-center justify-center transition-all ${mapStyle === 'satellite' ? 'bg-slate-200 text-slate-800' : 'hover:bg-slate-100 text-slate-500'}`}
                      title="Satellite View"
                    >
                      <span className="material-symbols-outlined">satellite_alt</span>
                    </button>
                  </div>

                  {/* NDVI Legend */}
                  <div className="absolute bottom-6 left-6 bg-white/90 backdrop-blur-md p-5 rounded-xl border border-slate-200 shadow-lg flex flex-col gap-3 z-[400]">
                    <p className="text-[10px] font-bold uppercase text-slate-500 tracking-widest">NDVI Index Legend</p>
                    <div className="flex flex-col gap-2.5">
                      <div className="flex items-center gap-3">
                        <div className="h-3 w-8 bg-[#10b77f] rounded-full" />
                        <span className="text-xs font-semibold text-slate-700">Dense (&gt;0.4)</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="h-3 w-8 bg-yellow-400 rounded-full" />
                        <span className="text-xs font-semibold text-slate-700">Moderate (0.2–0.4)</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="h-3 w-8 bg-orange-500 rounded-full" />
                        <span className="text-xs font-semibold text-slate-700">Exposed (&lt;0.2)</span>
                      </div>
                    </div>
                  </div>

                  {/* Loading overlay */}
                  {loading && (
                    <div className="absolute inset-0 bg-white/50 flex items-center justify-center z-[500]">
                      <div className="glass-panel p-4 rounded-xl flex items-center gap-3">
                        <span className="material-symbols-outlined text-primary animate-spin">refresh</span>
                        <span className="text-sm font-medium text-slate-700">Loading satellite data…</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Layer Selection */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <button className="p-4 bg-primary/10 border-2 border-primary rounded-xl flex items-center gap-3 text-primary transition-all">
                    <span className="material-symbols-outlined">eco</span>
                    <span className="text-sm font-bold">NDVI Density</span>
                  </button>
                  <button className="p-4 bg-white border border-slate-200 rounded-xl flex items-center gap-3 text-slate-400 cursor-not-allowed opacity-50 shadow-sm">
                    <span className="material-symbols-outlined">wb_sunny</span>
                    <span className="text-sm font-bold">Heat Index</span>
                  </button>
                  <button className="p-4 bg-white border border-slate-200 rounded-xl flex items-center gap-3 text-slate-400 cursor-not-allowed opacity-50 shadow-sm">
                    <span className="material-symbols-outlined">opacity</span>
                    <span className="text-sm font-bold">Soil Moisture</span>
                  </button>
                  <button className="p-4 bg-white border border-slate-200 rounded-xl flex items-center gap-3 text-slate-400 cursor-not-allowed opacity-50 shadow-sm">
                    <span className="material-symbols-outlined">cloud</span>
                    <span className="text-sm font-bold">CO₂ Capture</span>
                  </button>
                </div>
              </div>

              {/* Stats Panel */}
              <div className="flex flex-col gap-6">
                {/* Canopy Stats Card */}
                <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm flex flex-col gap-6">
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-slate-500 uppercase text-[10px] tracking-widest">Canopy Stats</h3>
                    <span className="material-symbols-outlined text-primary">analytics</span>
                  </div>
                  <div className="flex flex-col gap-5">
                    <div className="flex flex-col gap-1">
                      <span className="text-slate-400 text-xs font-semibold">Max NDVI Value</span>
                      <div className="flex items-end gap-2">
                        {loading
                          ? <StatSkeleton />
                          : <span className="text-3xl font-black text-slate-900">{maxNdvi}</span>
                        }
                      </div>
                    </div>
                    <div className="h-px w-full bg-slate-100" />
                    <div className="flex flex-col gap-4">
                      <div className="flex flex-col gap-2">
                        <div className="flex justify-between text-xs font-bold">
                          <span className="text-slate-600">Dense Canopy</span>
                          {loading ? <StatSkeleton /> : <span className="text-secondary">{densePct}%</span>}
                        </div>
                        <Bar value={densePct} color="bg-secondary" />
                      </div>
                      <div className="flex flex-col gap-2">
                        <div className="flex justify-between text-xs font-bold">
                          <span className="text-slate-600">Moderate</span>
                          {loading ? <StatSkeleton /> : <span className="text-yellow-500">{moderatePct}%</span>}
                        </div>
                        <Bar value={moderatePct} color="bg-yellow-400" />
                      </div>
                      <div className="flex flex-col gap-2">
                        <div className="flex justify-between text-xs font-bold">
                          <span className="text-slate-600">Exposed</span>
                          {loading ? <StatSkeleton /> : <span className="text-orange-500">{sparsePct}%</span>}
                        </div>
                        <Bar value={sparsePct} color="bg-orange-500" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Shade Quality */}
                <div className="bg-white border border-slate-200 p-6 rounded-2xl shadow-sm">
                  <div className="flex items-center gap-2 mb-5">
                    <span className="material-symbols-outlined text-primary">umbrella</span>
                    <h3 className="font-bold text-slate-500 uppercase text-[10px] tracking-widest">Shade Quality</h3>
                  </div>
                  <div className="flex flex-col gap-5">
                    <div className="flex items-center gap-4">
                      <div className="size-12 rounded-full bg-primary/10 flex items-center justify-center">
                        <span className="material-symbols-outlined text-primary">park</span>
                      </div>
                      <div>
                        <p className="text-2xl font-black text-slate-900">
                          {loading ? '…' : `${densePct}%`}
                        </p>
                        <p className="text-[10px] text-slate-400 uppercase font-bold">Dense Tree Cover</p>
                      </div>
                    </div>
                    <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                      <p className="text-xs text-slate-600 leading-relaxed">
                        Shade data sourced from <span className="text-secondary font-bold">Sentinel-2 NDVI</span> via Google Earth Engine. Updates every 10 minutes.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Alert if sparse */}
                {!loading && sparsePct > 40 && (
                  <div className="bg-orange-50 rounded-xl p-4 border border-orange-100">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="material-symbols-outlined text-orange-600 text-sm">warning</span>
                      <p className="text-[10px] text-orange-700 font-black uppercase tracking-wider">Coverage Alert</p>
                    </div>
                    <p className="text-xs text-orange-800 leading-relaxed font-medium">
                      {sparsePct}% of the area has low canopy density. Increased heat exposure in exposed zones.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}
