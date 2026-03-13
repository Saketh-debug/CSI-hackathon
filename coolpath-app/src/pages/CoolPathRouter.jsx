import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import { MapContainer, ImageOverlay, Polyline, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { useRoute, useTemperatureData, useCanopyData } from '../api/hooks'
import MapResizer from '../components/MapResizer'

// Component to imperatively fit map bounds when a new route is calculated
function RouteFitter({ result }) {
  const map = useMap()
  
  useEffect(() => {
    if (result && result.fastest?.coords?.length) {
      const allCoords = [
        ...result.fastest.coords,
        ...(result.coolest && !result.routes_identical ? result.coolest.coords : [])
      ]
      
      if (allCoords.length > 0) {
        // Calculate bounding box [ [minLat, minLon], [maxLat, maxLon] ]
        let minLat = Infinity, minLon = Infinity
        let maxLat = -Infinity, maxLon = -Infinity
        
        allCoords.forEach(([lat, lon]) => {
          if (lat < minLat) minLat = lat
          if (lat > maxLat) maxLat = lat
          if (lon < minLon) minLon = lon
          if (lon > maxLon) maxLon = lon
        })
        
        // Pad the bounds slightly and fit map
        map.fitBounds([ [minLat, minLon], [maxLat, maxLon] ], { padding: [50, 50] })
      }
    }
  }, [result, map])
  
  return null
}

export default function CoolPathRouter() {
  const navigate = useNavigate()
  const [origin, setOrigin]           = useState('Madhapur, Hyderabad')
  const [destination, setDestination] = useState('Banjara Hills, Hyderabad')
  const [shadeWeight, setShadeWeight] = useState(0.5)
  const [tempWeight, setTempWeight]   = useState(0.3)
  const [maxDev, setMaxDev]           = useState(1.3)

  const [activeLayer, setActiveLayer] = useState('heatmap')  // 'heatmap' | 'canopy' | null
  const [mapStyle, setMapStyle]       = useState('osm')      // 'osm' | 'satellite'

  const { result, loading, error, compute } = useRoute()
  const { data: tempData } = useTemperatureData()
  const { data: ndviData } = useCanopyData()

  const CENTER = [17.4474, 78.3762]
  const lstBounds  = tempData?.bounds ?? [[17.0, 77.9], [17.9, 78.8]]
  const ndviBounds = ndviData?.bounds ?? [[17.0, 77.9], [17.9, 78.8]]

  const fast = result?.fastest
  const cool = result?.coolest

  const formatTime = (min) => {
    if (!min) return '';
    const h = Math.floor(min / 60);
    const m = min % 60;
    return h > 0 ? `${h} hr ${m} min` : `${m} min`;
  };

  function handleCompute() {
    compute(origin, destination, { shade: shadeWeight, temp: tempWeight, maxDev })
  }

  // Swap origin/destination
  function handleSwap() {
    setOrigin(destination)
    setDestination(origin)
  }

  // Map center: fit to route if available, else Hyderabad
  const mapCenter = fast?.coords?.length
    ? [
        (fast.coords[0][0] + fast.coords[fast.coords.length - 1][0]) / 2,
        (fast.coords[0][1] + fast.coords[fast.coords.length - 1][1]) / 2,
      ]
    : CENTER

  return (
    <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-background-light font-display text-slate-900 antialiased">
      <Navbar />

      <main className="flex flex-1 flex-col lg:flex-row h-[calc(100vh-64px)] overflow-hidden">
        {/* ── Left Sidebar ── */}
        <div className="w-full lg:w-[420px] bg-white border-r border-slate-200 flex flex-col overflow-y-auto">

          {/* Input Panel */}
          <div className="p-6 space-y-4 border-b border-slate-100 bg-slate-50/50">
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-primary text-xl">travel_explore</span>
              <h3 className="font-semibold text-base text-slate-800">Plan Your CoolPath</h3>
            </div>

            <div className="space-y-3">
              <div className="relative">
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1 ml-1">Origin</label>
                <div className="flex items-center bg-white border border-slate-200 rounded-lg group focus-within:border-primary transition-colors shadow-sm">
                  <span className="material-symbols-outlined text-slate-400 ml-3">my_location</span>
                  <input
                    className="w-full bg-transparent border-none focus:ring-0 text-sm py-3 px-3 text-slate-700 placeholder:text-slate-400 outline-none"
                    placeholder="Enter starting point"
                    type="text"
                    value={origin}
                    onChange={e => setOrigin(e.target.value)}
                  />
                </div>
              </div>

              <div className="relative">
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1 ml-1">Destination</label>
                <div className="flex items-center bg-white border border-slate-200 rounded-lg group focus-within:border-primary transition-colors shadow-sm">
                  <span className="material-symbols-outlined text-slate-400 ml-3">location_on</span>
                  <input
                    className="w-full bg-transparent border-none focus:ring-0 text-sm py-3 px-3 text-slate-700 placeholder:text-slate-400 outline-none"
                    placeholder="Enter destination"
                    type="text"
                    value={destination}
                    onChange={e => setDestination(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                onClick={handleCompute}
                disabled={loading}
                className="flex-1 bg-primary text-white font-bold py-3 rounded-lg flex items-center justify-center gap-2 hover:bg-primary/90 transition-all shadow-md shadow-primary/20 disabled:opacity-60 disabled:cursor-wait"
              >
                {loading
                  ? <><span className="material-symbols-outlined text-xl animate-spin">refresh</span> Computing…</>
                  : <><span className="material-symbols-outlined text-xl">directions</span> Calculate Route</>
                }
              </button>
              <button
                onClick={handleSwap}
                className="w-12 bg-slate-100 text-slate-600 rounded-lg flex items-center justify-center hover:bg-slate-200 transition-colors"
                title="Swap origin/destination"
              >
                <span className="material-symbols-outlined">swap_vert</span>
              </button>
            </div>

            <button
              onClick={() => navigate('/walk-option')}
              className="w-full bg-emerald-50 text-emerald-700 font-bold py-2.5 rounded-lg flex items-center justify-center gap-2 border border-emerald-200 hover:bg-emerald-100 transition-all"
            >
              <span className="material-symbols-outlined">directions_walk</span>
              Walk Option
            </button>

            {/* Error display */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700 flex items-start gap-2">
                <span className="material-symbols-outlined text-sm mt-0.5">error</span>
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* Routing Weights */}
          <div className="p-5 border-b border-slate-100">
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">Routing Weights</h4>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-600 font-medium">🌳 Shade importance</span>
                  <span className="font-bold text-primary">{shadeWeight.toFixed(2)}</span>
                </div>
                <input type="range" min="0" max="1" step="0.05" value={shadeWeight}
                  onChange={e => setShadeWeight(parseFloat(e.target.value))}
                  className="w-full accent-primary" />
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-600 font-medium">🌡️ Temp avoidance</span>
                  <span className="font-bold text-primary">{tempWeight.toFixed(2)}</span>
                </div>
                <input type="range" min="0" max="1" step="0.05" value={tempWeight}
                  onChange={e => setTempWeight(parseFloat(e.target.value))}
                  className="w-full accent-primary" />
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-600 font-medium">📐 Max deviation</span>
                  <span className="font-bold text-primary">{maxDev.toFixed(1)}×</span>
                </div>
                <input type="range" min="1" max="2" step="0.1" value={maxDev}
                  onChange={e => setMaxDev(parseFloat(e.target.value))}
                  className="w-full accent-primary" />
              </div>
            </div>
          </div>

          {/* Comparison Table */}
          <div className="p-6 flex-1">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center justify-between">
              Route Comparison
              {result && !result.routes_identical && (
                <span className="bg-success/10 text-success px-2 py-0.5 rounded text-[10px]">Optimized for shade</span>
              )}
            </h4>

            {!result && !loading && (
              <div className="text-center py-10 text-slate-400">
                <span className="material-symbols-outlined text-4xl mb-2 block">route</span>
                <p className="text-sm">Enter origin &amp; destination above, then click Calculate Route.</p>
              </div>
            )}

            {result && (
              <div className="space-y-4">
                {/* Fastest Route Card */}
                <div className="p-4 rounded-xl border border-slate-200 bg-white hover:border-slate-300 cursor-pointer transition-all shadow-sm">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <span className="bg-red-50 text-red-500 text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wide">Fastest Route</span>
                      <h5 className="text-lg font-bold mt-1 text-slate-800 flex items-baseline gap-1.5">
                        {fast.distance_km} km
                        {fast.duration_min && <span className="text-sm font-medium text-slate-400">• {formatTime(fast.duration_min)}</span>}
                      </h5>
                      {result.origin?.address && (
                        <p className="text-[10px] text-slate-400 mt-0.5 truncate max-w-[200px]">{result.origin.address.split(',').slice(0, 2).join(',')}</p>
                      )}
                    </div>
                    <span className="material-symbols-outlined text-red-500">dangerous</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <p className="text-[10px] text-slate-400 uppercase font-bold">Shade %</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-red-400 rounded-full" style={{ width: `${fast.stats.shade_pct}%` }} />
                        </div>
                        <span className="text-xs font-bold text-slate-600">{fast.stats.shade_pct}%</span>
                      </div>
                    </div>
                    <div className="space-y-1">
                      <p className="text-[10px] text-slate-400 uppercase font-bold">Heat Exposure</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-red-500 rounded-full" style={{ width: `${Math.round(fast.stats.avg_temp_score * 100)}%` }} />
                        </div>
                        <span className="text-xs font-bold text-slate-600">
                          {fast.stats.avg_temp_score > 0.66 ? 'High' : fast.stats.avg_temp_score > 0.33 ? 'Med' : 'Low'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* CoolPath Route Card */}
                <div className="p-4 rounded-xl border-2 border-success bg-success/5 cursor-pointer transition-all shadow-lg shadow-success/5 ring-4 ring-success/5">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <span className="bg-success text-white text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wide">CoolPath Route</span>
                      <h5 className="text-lg font-bold mt-1 text-success flex items-baseline gap-1.5">
                        {cool.distance_km} km
                        {cool.duration_min && <span className="text-sm font-medium text-success/70">• {formatTime(cool.duration_min)}</span>}
                      </h5>
                    </div>
                    <span className="material-symbols-outlined text-success fill-1">verified</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <p className="text-[10px] text-success/70 uppercase font-bold">Shade %</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-success/20 rounded-full overflow-hidden">
                          <div className="h-full bg-success rounded-full" style={{ width: `${cool.stats.shade_pct}%` }} />
                        </div>
                        <span className="text-xs font-bold text-success">{cool.stats.shade_pct}%</span>
                      </div>
                    </div>
                    <div className="space-y-1">
                      <p className="text-[10px] text-success/70 uppercase font-bold">Heat Exposure</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-success/20 rounded-full overflow-hidden">
                          <div className="h-full bg-success rounded-full" style={{ width: `${Math.round(cool.stats.avg_temp_score * 100)}%` }} />
                        </div>
                        <span className="text-xs font-bold text-success">
                          {cool.stats.avg_temp_score > 0.66 ? 'High' : cool.stats.avg_temp_score > 0.33 ? 'Med' : 'Low'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-success/20 flex justify-between items-center">
                    <span className="text-[10px] font-bold text-success/60 uppercase">Extra distance</span>
                    <span className="text-xs font-bold text-success">+{cool.deviation_pct}%</span>
                  </div>
                </div>

                {/* Insight callout */}
                {result.routes_identical ? (
                  <div className="mt-4 p-4 rounded-lg bg-sky-50 border border-sky-100">
                    <p className="text-xs leading-relaxed text-slate-500 italic">
                      <span className="font-bold text-primary">Note:</span> Both routes are identical — the fastest path already has good shade coverage in this area.
                    </p>
                  </div>
                ) : (
                  <div className="mt-4 p-4 rounded-lg bg-sky-50 border border-sky-100">
                    <p className="text-xs leading-relaxed text-slate-500 italic">
                      <span className="font-bold text-primary">CoolPath:</span> {cool.stats.shade_pct - fast.stats.shade_pct > 0
                        ? `Gives ${(cool.stats.shade_pct - fast.stats.shade_pct).toFixed(0)}% more shade with only +${cool.deviation_pct}% extra distance.`
                        : `Avoids hotter zones while staying close to the fastest path.`}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Map Area ── */}
        <div className="flex-1 relative" style={{ minHeight: '400px' }}>
          <MapContainer
            center={mapCenter}
            zoom={result ? 13 : 11}
            style={{ width: '100%', height: '100%', zIndex: 0 }}
            attributionControl={false}
          >
            <MapResizer />
            <RouteFitter result={result} />
            
            {mapStyle === 'osm' ? (
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            ) : (
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attribution="Esri"
              />
            )}
            
            {/* LST overlay at 35% opacity */}
            {activeLayer === 'heatmap' && tempData?.image_url && (
              <ImageOverlay url={tempData.image_url} bounds={lstBounds} opacity={0.35} />
            )}
            {/* NDVI overlay at 30% opacity */}
            {activeLayer === 'canopy' && ndviData?.image_url && (
              <ImageOverlay url={ndviData.image_url} bounds={ndviBounds} opacity={0.30} />
            )}

            {/* Routes */}
            {fast?.coords?.length && (
              <Polyline
                positions={fast.coords}
                pathOptions={{ color: '#ef4444', weight: 5, opacity: 0.85, dashArray: '10 6' }}
              />
            )}
            {cool?.coords?.length && !result?.routes_identical && (
              <Polyline
                positions={cool.coords}
                pathOptions={{ color: '#10b77f', weight: 7, opacity: 0.95 }}
              />
            )}

            {/* Markers */}
            {fast?.coords?.length && (
              <>
                <Marker position={fast.coords[0]}>
                  <Popup>📍 {result?.origin?.address?.split(',')[0] ?? 'Origin'}</Popup>
                </Marker>
                <Marker position={fast.coords[fast.coords.length - 1]}>
                  <Popup>🏁 {result?.destination?.address?.split(',')[0] ?? 'Destination'}</Popup>
                </Marker>
              </>
            )}
          </MapContainer>

          {/* Layer Controls overlay */}
          <div className="absolute top-6 left-6 z-[400] flex flex-col gap-3">
            {/* Base map toggles */}
            <div className="bg-white/90 backdrop-blur-md rounded-xl shadow-xl border border-slate-200 p-1.5 flex flex-col">
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

            {/* Overlays */}
            <div className="bg-white/90 backdrop-blur-md rounded-xl shadow-xl border border-slate-200 p-1.5 flex flex-col">
              <button
                onClick={() => setActiveLayer(prev => prev === 'heatmap' ? null : 'heatmap')}
                className={`p-2.5 rounded-lg flex items-center gap-3 transition-all ${activeLayer === 'heatmap' ? 'bg-primary/10 text-primary' : 'hover:bg-slate-100 text-slate-500'}`}
              >
                <span className="material-symbols-outlined">thermostat</span>
                <span className="text-xs font-bold uppercase pr-2">Heatmap</span>
              </button>
              <div className="h-[1px] bg-slate-100 mx-2 my-1" />
              <button
                onClick={() => setActiveLayer(prev => prev === 'canopy' ? null : 'canopy')}
                className={`p-2.5 rounded-lg flex items-center gap-3 transition-all ${activeLayer === 'canopy' ? 'bg-emerald-50 text-emerald-600' : 'hover:bg-slate-100 text-slate-500'}`}
              >
                <span className="material-symbols-outlined">park</span>
                <span className="text-xs font-bold uppercase pr-2">Tree Canopy</span>
              </button>
            </div>
          </div>

          {/* Legend */}
          <div className="absolute bottom-6 left-6 z-[400]">
            <div className="bg-white/90 backdrop-blur-md rounded-xl shadow-xl border border-slate-200 p-4 min-w-[200px]">
              <h6 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">Map Legend</h6>
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-1.5 bg-success rounded-full" />
                  <span className="text-xs font-semibold text-slate-700">CoolPath Route</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-6 h-0 border-b-2 border-dashed border-red-500" />
                  <span className="text-xs font-semibold text-slate-700">Fastest Route</span>
                </div>
                <div className="flex items-center gap-3 pt-1">
                  <div className="w-24 h-2 rounded-full bg-gradient-to-r from-success via-yellow-400 to-red-500" />
                  <span className="text-[10px] font-bold uppercase text-slate-400">Temp</span>
                </div>
              </div>
            </div>
          </div>

          {/* Loading overlay on map */}
          {loading && (
            <div className="absolute inset-0 bg-white/40 z-[500] flex items-center justify-center">
              <div className="bg-white rounded-xl shadow-xl p-5 flex items-center gap-3">
                <span className="material-symbols-outlined text-primary text-2xl animate-spin">refresh</span>
                <div>
                  <p className="font-bold text-slate-800">Computing routes…</p>
                  <p className="text-xs text-slate-500">Geocoding &amp; running climate-aware routing</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
