import { useState } from 'react'
import Navbar from '../components/Navbar'
import { MapContainer, ImageOverlay, TileLayer } from 'react-leaflet'
import { useTemperatureData, useForecastData } from '../api/hooks'
import MapResizer from '../components/MapResizer'

// Weather icon mapping for hourly forecast
const WEATHER_ICONS = {
  0: 'wb_sunny', 1: 'wb_sunny', 2: 'partly_cloudy_day', 3: 'wb_cloudy',
  45: 'foggy', 48: 'foggy', 51: 'grain', 53: 'grain', 55: 'grain',
  61: 'rainy', 63: 'rainy', 65: 'rainy', 80: 'rainy', 81: 'rainy', 82: 'rainy',
}
function weatherIcon(temp) {
  if (temp > 32) return 'wb_sunny'
  if (temp > 25) return 'partly_cloudy_day'
  if (temp > 18) return 'wb_cloudy'
  return 'cloud'
}

// Skeleton placeholder for loading state
function StatSkeleton() {
  return (
    <div className="animate-pulse flex flex-col gap-2">
      <div className="h-5 w-16 bg-slate-200 rounded" />
      <div className="h-7 w-24 bg-slate-200 rounded" />
    </div>
  )
}

export default function Heatmap() {
  const [showForecast, setShowForecast] = useState(true)
  const [mapStyle, setMapStyle] = useState('osm') // 'osm' | 'satellite'
  const { data: tempData, loading: tempLoading, error: tempError } = useTemperatureData()
  const { data: forecast, loading: forecastLoading } = useForecastData()

  // Derive Leaflet bounds: [[south, west], [north, east]]
  const mapBounds = tempData?.bounds ?? [[17.0, 77.9], [17.9, 78.8]]
  const CENTER = [17.4474, 78.3762]

  // Build 24-hour forecast items from API data
  const forecastItems = (() => {
    if (!forecast?.available || !forecast.times?.length) return []
    const now = new Date()
    let startIndex = forecast.times.findIndex(t => {
      const d = new Date(t)
      return d.getTime() >= now.getTime() || (d.getHours() === now.getHours() && d.getDate() === now.getDate())
    })
    if (startIndex === -1) startIndex = 0

    return forecast.times.slice(startIndex, startIndex + 24).map((t, i) => {
      const idx = startIndex + i
      return {
        time: t.split('T')[1]?.slice(0, 5) ?? '',
        temp: forecast.temps[idx] ?? 0,
        feel: forecast.apparent[idx] ?? 0,
        icon: weatherIcon(forecast.temps[idx] ?? 25),
      }
    })
  })()

  const minT = tempData?.min_temp ?? '—'
  const avgT = tempData?.avg_temp ?? '—'
  const maxT = tempData?.max_temp ?? '—'

  return (
    <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-background-light text-slate-900">
      <Navbar />

      <main className="flex-1 flex flex-col relative" style={{ minHeight: '100vh' }}>
        {/* Fullscreen Map */}
        <div className="absolute inset-0 z-0 bg-slate-100">
          <MapContainer
            center={CENTER}
            zoom={11}
            style={{ width: '100%', height: '100%' }}
            zoomControl={false}
            attributionControl={false}
          >
            <MapResizer />
            {/* Base tiles */}
            {mapStyle === 'osm' ? (
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            ) : (
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attribution="Esri"
              />
            )}
            {/* LST heatmap overlay at 72% opacity */}
            {tempData?.image_url && (
              <ImageOverlay
                url={tempData.image_url}
                bounds={mapBounds}
                opacity={0.72}
              />
            )}
          </MapContainer>
          <div className="absolute inset-0 bg-gradient-to-r from-background-light/90 via-transparent to-transparent pointer-events-none" />
          <div className="absolute inset-0 bg-gradient-to-t from-background-light/50 via-transparent to-transparent pointer-events-none" />

          {/* Map Style Controls (Floating Right) */}
          <div className="absolute top-6 right-6 bg-white/90 backdrop-blur-md rounded-xl shadow-xl border border-slate-200 p-1.5 flex flex-col z-10 pointer-events-auto gap-1">
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
        </div>

        {/* Dashboard Content */}
        <div className="relative z-10 flex flex-col h-full p-6 pointer-events-none">
          <div className="flex flex-col lg:flex-row gap-6 h-full items-start">
            {/* Left Sidebar */}
            <div className="w-full lg:w-80 flex flex-col gap-4 pointer-events-auto">
              {/* Stats Panel */}
              <div className="glass-panel p-5 rounded-xl shadow-lg border-slate-200">
                <h3 className="text-slate-500 text-xs font-bold uppercase tracking-widest mb-4">
                  Land Surface Temp
                </h3>
                {tempError && (
                  <p className="text-red-500 text-xs mb-2">⚠️ {tempError}</p>
                )}
                <div className="grid grid-cols-1 gap-4">
                  {/* Min */}
                  <div className="flex items-center justify-between p-3 rounded-lg bg-white/50 border border-slate-100">
                    <div className="flex items-center gap-3">
                      <div className="size-8 rounded-md bg-blue-100 flex items-center justify-center">
                        <span className="material-symbols-outlined text-blue-500 text-lg">ac_unit</span>
                      </div>
                      <div>
                        <p className="text-slate-400 text-[10px] font-medium uppercase leading-none mb-1">Min</p>
                        {tempLoading
                          ? <StatSkeleton />
                          : <p className="text-slate-900 text-xl font-bold leading-none">{minT}°C</p>
                        }
                      </div>
                    </div>
                  </div>
                  {/* Avg */}
                  <div className="flex items-center justify-between p-3 rounded-lg bg-white/50 border border-slate-100">
                    <div className="flex items-center gap-3">
                      <div className="size-8 rounded-md bg-yellow-100 flex items-center justify-center">
                        <span className="material-symbols-outlined text-yellow-600 text-lg">wb_sunny</span>
                      </div>
                      <div>
                        <p className="text-slate-400 text-[10px] font-medium uppercase leading-none mb-1">Average</p>
                        {tempLoading
                          ? <StatSkeleton />
                          : <p className="text-slate-900 text-xl font-bold leading-none">{avgT}°C</p>
                        }
                      </div>
                    </div>
                  </div>
                  {/* Max */}
                  <div className="flex items-center justify-between p-3 rounded-lg bg-white/50 border border-slate-100">
                    <div className="flex items-center gap-3">
                      <div className="size-8 rounded-md bg-red-100 flex items-center justify-center">
                        <span className="material-symbols-outlined text-red-500 text-lg">local_fire_department</span>
                      </div>
                      <div>
                        <p className="text-slate-400 text-[10px] font-medium uppercase leading-none mb-1">Max</p>
                        {tempLoading
                          ? <StatSkeleton />
                          : <p className="text-red-600 text-xl font-bold leading-none">{maxT}°C</p>
                        }
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* View Layers Toggle */}
              <div className="glass-panel p-5 rounded-xl shadow-lg border-slate-200">
                <h3 className="text-slate-500 text-xs font-bold uppercase tracking-widest mb-4">View Layers</h3>
                <div className="space-y-3">
                  <label className="flex items-center justify-between group cursor-pointer pointer-events-auto">
                    <span className="text-slate-700 text-sm group-hover:text-primary transition-colors">Show 24-Hour Forecast</span>
                    <div className="relative inline-flex items-center cursor-pointer">
                      <input
                        checked={showForecast}
                        onChange={e => setShowForecast(e.target.checked)}
                        className="sr-only peer"
                        type="checkbox"
                      />
                      <div className="w-10 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary" />
                    </div>
                  </label>
                </div>
              </div>

              {/* Legend */}
              <div className="glass-panel p-5 rounded-xl shadow-lg border-slate-200">
                <h3 className="text-slate-500 text-xs font-bold uppercase tracking-widest mb-4">Legend</h3>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-medium">{minT}°C</span>
                  <div className="h-2 flex-1 rounded-full bg-gradient-to-r from-blue-500 via-yellow-400 to-red-500 border border-slate-200" />
                  <span className="text-xs text-slate-500 font-medium">{maxT}°C</span>
                </div>
              </div>
            </div>

            {/* Forecast Panel */}
            {showForecast && (
              <div className="flex-1 flex flex-col justify-end h-full w-full">
                <div className="glass-panel p-6 rounded-xl shadow-xl border-slate-200 pointer-events-auto">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-slate-900 text-lg font-bold">24-Hour Forecast</h3>
                      {forecast?.available && (
                        <p className="text-slate-500 text-xs">
                          Now: <span className="font-bold">{forecast.current_temp}°C</span>
                          {' '}(feels {forecast.current_apparent}°C) — {forecast.weather_description}
                        </p>
                      )}
                      {!forecast?.available && !forecastLoading && (
                        <p className="text-slate-400 text-xs">Forecast temporarily unavailable</p>
                      )}
                    </div>
                    <div className="flex gap-2">

                    </div>
                  </div>

                  {forecastLoading ? (
                    <div className="h-48 flex items-center justify-center">
                      <span className="text-slate-400 text-sm animate-pulse">Loading forecast…</span>
                    </div>
                  ) : (() => {
                    // Use real data or generate plausible placeholder data
                    const items = forecastItems.length
                      ? forecastItems
                      : Array.from({ length: 9 }, (_, i) => {
                        const baseTemp = 28 + Math.round(Math.sin((i / 8) * Math.PI) * 6)
                        const d = new Date()
                        d.setHours(d.getHours() + i * 3)
                        return {
                          time: `${d.getHours()}:00`.replace(/^\d:/, h => `0${h}`),
                          temp: baseTemp,
                          feel: baseTemp - 2,
                          icon: weatherIcon(baseTemp),
                        }
                      })

                    // Subsample to at most 9 columns so labels don't crowd
                    const MAX_COLS = 9
                    const step = Math.max(1, Math.floor(items.length / MAX_COLS))
                    const cols = items.filter((_, i) => i % step === 0).slice(0, MAX_COLS)

                    const temps = cols.map(c => c.temp)
                    const minT2 = Math.min(...temps)
                    const maxT2 = Math.max(...temps)
                    const range2 = maxT2 - minT2 || 1

                    // SVG dimensions
                    const W = 800
                    const H = 80          // chart area height (px in viewBox units)
                    const PAD_X = 40      // left/right padding so dots don't clip
                    const PAD_TOP = 22    // room for temp labels above the curve
                    const PAD_BOT = 4

                    const colW = (W - PAD_X * 2) / (cols.length - 1)

                    // Map a temperature to y (higher temp = higher on screen = lower y)
                    const toY = (t) => PAD_TOP + H - PAD_BOT - ((t - minT2) / range2) * (H - PAD_TOP - PAD_BOT)

                    // Build SVG polyline points
                    const points = cols.map((c, i) => `${PAD_X + i * colW},${toY(c.temp)}`).join(' ')

                    // Build a closed SVG polygon for the filled area (down to bottom)
                    const areaPoints = [
                      `${PAD_X},${H + PAD_TOP}`,
                      ...cols.map((c, i) => `${PAD_X + i * colW},${toY(c.temp)}`),
                      `${PAD_X + (cols.length - 1) * colW},${H + PAD_TOP}`,
                    ].join(' ')

                    // Day label: derive from index relative to "now"
                    const DAY_ABBR = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
                    const dayLabel = (col, i) => {
                      // Estimate which step in items this col corresponds to
                      const itemIndex = i * step
                      const hoursAhead = itemIndex // each item = 1 hour
                      const d = new Date()
                      d.setHours(d.getHours() + hoursAhead)
                      return DAY_ABBR[d.getDay()]
                    }

                    return (
                      <div className="w-full overflow-x-auto">
                        {/* SVG Chart */}
                        <svg
                          viewBox={`0 0 ${W} ${H + PAD_TOP}`}
                          className="w-full"
                          style={{ height: '110px', display: 'block' }}
                          preserveAspectRatio="none"
                        >
                          <defs>
                            <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#f59e0b" stopOpacity="0.35" />
                              <stop offset="100%" stopColor="#f59e0b" stopOpacity="0.04" />
                            </linearGradient>
                          </defs>

                          {/* Filled area under curve */}
                          <polygon points={areaPoints} fill="url(#areaGrad)" />

                          {/* Curve line */}
                          <polyline
                            points={points}
                            fill="none"
                            stroke="#f59e0b"
                            strokeWidth="2.5"
                            strokeLinejoin="round"
                            strokeLinecap="round"
                          />

                          {/* Dots + temperature labels */}
                          {cols.map((col, i) => {
                            const cx = PAD_X + i * colW
                            const cy = toY(col.temp)
                            return (
                              <g key={i}>
                                <circle cx={cx} cy={cy} r="4" fill="#f59e0b" stroke="white" strokeWidth="1.5" />
                                <text
                                  x={cx}
                                  y={cy - 8}
                                  textAnchor="middle"
                                  fontSize="11"
                                  fontWeight="600"
                                  fill="#475569"
                                >
                                  {col.temp}
                                </text>
                              </g>
                            )
                          })}
                        </svg>

                        {/* Time labels row */}
                        <div
                          className="grid w-full px-0"
                          style={{ gridTemplateColumns: `repeat(${cols.length}, 1fr)` }}
                        >
                          {cols.map((col, i) => (
                            <p key={i} className="text-center text-[10px] text-slate-400 font-medium leading-none mt-1">
                              {col.time}
                            </p>
                          ))}
                        </div>

                        {/* Divider */}
                        <div className="border-t border-slate-100 my-2" />

                        {/* Icons + day labels row */}
                        <div
                          className="grid w-full"
                          style={{ gridTemplateColumns: `repeat(${cols.length}, 1fr)` }}
                        >
                          {cols.map((col, i) => (
                            <div key={i} className={`flex flex-col items-center gap-0.5 py-1 rounded-lg ${i === 0 ? 'bg-slate-800' : ''}`}>
                              <p className={`text-[10px] font-bold leading-none ${i === 0 ? 'text-white' : 'text-slate-500'}`}>
                                {dayLabel(col, i)}
                              </p>
                              <span className={`material-symbols-outlined text-xl ${col.temp > 32 ? 'text-yellow-500' : col.temp > 26 ? 'text-yellow-400' : 'text-slate-400'}`}>
                                {col.icon}
                              </span>
                              <p className={`text-[10px] font-semibold leading-none ${i === 0 ? 'text-white' : 'text-slate-600'}`}>
                                {col.temp}° <span className="font-normal opacity-60">{col.feel}°</span>
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })()}
                </div>
              </div>
            )}


          </div>
        </div>
      </main>
    </div>
  )
}
