import { useEffect, useMemo, useState } from 'react'
import { ImageOverlay, MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import Navbar from '../components/Navbar'
import MapResizer from '../components/MapResizer'
import { useWalkRoute, useWalkabilityData } from '../api/hooks'

function RouteFitter({ coords }) {
  const map = useMap()

  useEffect(() => {
    if (!coords?.length) return

    let minLat = Infinity
    let minLon = Infinity
    let maxLat = -Infinity
    let maxLon = -Infinity

    coords.forEach(([lat, lon]) => {
      if (lat < minLat) minLat = lat
      if (lat > maxLat) maxLat = lat
      if (lon < minLon) minLon = lon
      if (lon > maxLon) maxLon = lon
    })

    map.fitBounds([[minLat, minLon], [maxLat, maxLon]], { padding: [50, 50] })
  }, [coords, map])

  return null
}

function formatBestHours(hours) {
  if (!hours?.length) return 'No low-UV windows detected right now.'

  const sorted = [...new Set(hours)].sort((a, b) => a - b)
  const ranges = []
  let start = sorted[0]
  let end = sorted[0]

  for (let i = 1; i < sorted.length; i += 1) {
    if (sorted[i] === end + 1) {
      end = sorted[i]
    } else {
      ranges.push([start, end])
      start = sorted[i]
      end = sorted[i]
    }
  }
  ranges.push([start, end])

  const hh = (value) => `${String(value).padStart(2, '0')}:00`
  return ranges
    .map(([s, e]) => `${hh(s)}-${hh((e + 1) % 24)}`)
    .join(' · ')
}

export default function WalkOption() {
  const [origin, setOrigin] = useState('Madhapur, Hyderabad')
  const [destination, setDestination] = useState('KBR Park, Banjara Hills, Hyderabad')
  const [mapStyle, setMapStyle] = useState('osm')
  const [showLayer, setShowLayer] = useState(true)

  const { data: walkabilityData, loading: walkabilityLoading, error: walkabilityError } = useWalkabilityData()
  const { result, loading, error, compute } = useWalkRoute()

  const route = result?.route
  const routeCoords = route?.coords ?? []
  const bestHours = result?.best_hours ?? walkabilityData?.best_hours ?? []
  const walkabilityStats = result?.walkability_stats ?? walkabilityData?.stats ?? {}
  const mapBounds = walkabilityData?.bounds ?? [[17.0, 77.9], [17.9, 78.8]]
  const center = [17.4474, 78.3762]

  const mapCenter = useMemo(() => {
    if (!routeCoords.length) return center
    return [
      (routeCoords[0][0] + routeCoords[routeCoords.length - 1][0]) / 2,
      (routeCoords[0][1] + routeCoords[routeCoords.length - 1][1]) / 2,
    ]
  }, [routeCoords])

  const isFiniteNumber = (value) => typeof value === 'number' && Number.isFinite(value)
  const distanceKm = isFiniteNumber(route?.distance_km) ? route.distance_km : null
  const routeScore = isFiniteNumber(route?.walk_score) ? route.walk_score : null
  const walkScore = routeScore ?? (isFiniteNumber(walkabilityStats.avg_score) ? walkabilityStats.avg_score : null)
  const uvIndex = isFiniteNumber(walkabilityStats.max_uv) ? walkabilityStats.max_uv : null
  const aqi = isFiniteNumber(walkabilityStats.avg_aqi) ? walkabilityStats.avg_aqi : null
  const slopeDeg = isFiniteNumber(walkabilityStats.avg_slope_deg) ? walkabilityStats.avg_slope_deg : null

  const walkScoreColor =
    walkScore == null ? 'text-slate-400' : walkScore >= 70 ? 'text-emerald-600' : walkScore >= 40 ? 'text-amber-600' : 'text-red-600'
  const uvColor =
    uvIndex == null ? 'text-slate-400' : uvIndex < 3 ? 'text-emerald-600' : uvIndex < 6 ? 'text-amber-600' : 'text-red-500'
  const aqiColor =
    aqi == null ? 'text-slate-400' : aqi <= 50 ? 'text-emerald-600' : aqi <= 100 ? 'text-amber-600' : 'text-red-500'
  const slopeLabel = slopeDeg == null ? 'Unknown' : slopeDeg <= 2 ? 'Flat' : slopeDeg <= 6 ? 'Gentle' : 'Steep'

  function handleCompute() {
    compute(origin, destination)
  }

  function handleSwap() {
    setOrigin(destination)
    setDestination(origin)
  }

  return (
    <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-background-light font-display text-slate-900 antialiased">
      <Navbar />

      <main className="flex flex-1 flex-col lg:flex-row h-[calc(100vh-64px)] overflow-hidden">
        <div className="w-full lg:w-[420px] bg-white border-r border-slate-200 flex flex-col overflow-y-auto">
          <div className="p-6 space-y-4 border-b border-slate-100 bg-slate-50/50">
            <div className="flex items-center gap-2 mb-2">
              <span className="material-symbols-outlined text-primary text-xl">directions_walk</span>
              <h3 className="font-semibold text-base text-slate-800">Plan Walk Option</h3>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1 ml-1">Origin</label>
                <div className="flex items-center bg-white border border-slate-200 rounded-lg group focus-within:border-primary transition-colors shadow-sm">
                  <span className="material-symbols-outlined text-slate-400 ml-3">my_location</span>
                  <input
                    className="w-full bg-transparent border-none focus:ring-0 text-sm py-3 px-3 text-slate-700 placeholder:text-slate-400 outline-none"
                    placeholder="Enter starting point"
                    type="text"
                    value={origin}
                    onChange={(e) => setOrigin(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1 ml-1">Destination</label>
                <div className="flex items-center bg-white border border-slate-200 rounded-lg group focus-within:border-primary transition-colors shadow-sm">
                  <span className="material-symbols-outlined text-slate-400 ml-3">location_on</span>
                  <input
                    className="w-full bg-transparent border-none focus:ring-0 text-sm py-3 px-3 text-slate-700 placeholder:text-slate-400 outline-none"
                    placeholder="Enter destination"
                    type="text"
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
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
                {loading ? (
                  <>
                    <span className="material-symbols-outlined text-xl animate-spin">refresh</span>
                    Computing...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-xl">directions_walk</span>
                    Find Walk Path
                  </>
                )}
              </button>
              <button
                onClick={handleSwap}
                className="w-12 bg-slate-100 text-slate-600 rounded-lg flex items-center justify-center hover:bg-slate-200 transition-colors"
                title="Swap origin/destination"
              >
                <span className="material-symbols-outlined">swap_vert</span>
              </button>
            </div>

            {(error || walkabilityError) && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700 flex items-start gap-2">
                <span className="material-symbols-outlined text-sm mt-0.5">error</span>
                <span>{error || walkabilityError}</span>
              </div>
            )}
          </div>

          <div className="p-5 border-b border-slate-100">
            <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">Walkability Snapshot</h4>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <p className="text-[10px] text-slate-400 uppercase font-bold">Distance</p>
                <p className="text-xl font-bold text-emerald-600">{distanceKm == null ? '--' : `${distanceKm.toFixed(2)} km`}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <p className="text-[10px] text-slate-400 uppercase font-bold">Walk Score</p>
                <p className={`text-xl font-bold ${walkScoreColor}`}>{walkScore == null ? '--' : walkScore.toFixed(1)}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <p className="text-[10px] text-slate-400 uppercase font-bold">UV Index</p>
                <p className={`text-xl font-bold ${uvColor}`}>{uvIndex == null ? '--' : uvIndex.toFixed(1)}</p>
              </div>
              <div className="rounded-lg border border-slate-200 bg-white p-3">
                <p className="text-[10px] text-slate-400 uppercase font-bold">AQI</p>
                <p className={`text-xl font-bold ${aqiColor}`}>{aqi == null ? '--' : Math.round(aqi)}</p>
              </div>
            </div>
            <div className="mt-3 rounded-lg border border-sky-100 bg-sky-50 p-3 text-xs text-slate-600">
              <span className="font-bold text-primary">Best walking windows today:</span> {formatBestHours(bestHours)}
            </div>
            <div className="mt-3 rounded-lg border border-sky-100 bg-sky-50 p-3 text-xs text-slate-600">
              <span className="font-bold text-primary">Avg Slope: </span>{slopeDeg == null ? '--' : `${slopeDeg.toFixed(1)}°`} ({slopeLabel})
            </div>
          </div>

          

          <div className="p-6 flex-1">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Walk Route Result</h4>

            {!route && !loading && (
              <div className="text-center py-10 text-slate-400">
                <span className="material-symbols-outlined text-4xl mb-2 block">hiking</span>
                <p className="text-sm">Enter origin and destination, then click Find Walk Path.</p>
              </div>
            )}

            {route && (
              <div className="space-y-4">
                <div className="p-4 rounded-xl border-2 border-emerald-200 bg-emerald-50/60 shadow-sm">
                  <p className="text-[10px] text-emerald-700 uppercase font-bold tracking-wide">WalkWise Route</p>
                  <h5 className="text-2xl font-bold text-emerald-700 mt-1">{distanceKm == null ? '--' : `${distanceKm.toFixed(2)} km`}</h5>
                  <p className="text-xs text-slate-500 mt-1">
                    Score: <span className="font-bold text-slate-700">{routeScore == null ? '--' : routeScore.toFixed(1)}</span>
                  </p>
                </div>

                <div className="rounded-lg border border-slate-200 bg-white p-4 text-xs text-slate-600 space-y-2">
                  <p>
                    <span className="font-bold text-slate-700">From:</span> {result?.origin?.address}
                  </p>
                  <p>
                    <span className="font-bold text-slate-700">To:</span> {result?.destination?.address}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 relative" style={{ minHeight: '400px' }}>
          <MapContainer
            center={mapCenter}
            zoom={route ? 13 : 11}
            style={{ width: '100%', height: '100%', zIndex: 0 }}
            attributionControl={false}
          >
            <MapResizer />
            <RouteFitter coords={routeCoords} />

            {mapStyle === 'osm' ? (
              <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            ) : (
              <TileLayer
                url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                attribution="Esri"
              />
            )}

            {showLayer && walkabilityData?.image_url && (
              <ImageOverlay url={walkabilityData.image_url} bounds={mapBounds} opacity={0.5} />
            )}

            {routeCoords?.length > 0 && (
              <Polyline
                positions={routeCoords}
                pathOptions={{ color: '#22c55e', weight: 7, opacity: 0.95 }}
              />
            )}

            {routeCoords?.length > 0 && (
              <>
                <Marker position={routeCoords[0]}>
                  <Popup>Origin</Popup>
                </Marker>
                <Marker position={routeCoords[routeCoords.length - 1]}>
                  <Popup>Destination</Popup>
                </Marker>
              </>
            )}
          </MapContainer>

          <div className="absolute top-6 left-6 z-[400] flex flex-col gap-3">
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

            <div className="bg-white/90 backdrop-blur-md rounded-xl shadow-xl border border-slate-200 p-1.5 flex flex-col">
              <button
                onClick={() => setShowLayer((prev) => !prev)}
                className={`p-2.5 rounded-lg flex items-center gap-3 transition-all ${showLayer ? 'bg-emerald-50 text-emerald-600' : 'hover:bg-slate-100 text-slate-500'}`}
              >
                <span className="material-symbols-outlined">footprint</span>
                <span className="text-xs font-bold uppercase pr-2">Walkability</span>
              </button>
            </div>
          </div>

          <div className="absolute bottom-6 left-6 z-[400]">
            <div className="bg-white/90 backdrop-blur-md rounded-xl shadow-xl border border-slate-200 p-4 min-w-[220px]">
              <h6 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">Map Legend</h6>
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-1.5 bg-emerald-500 rounded-full" />
                  <span className="text-xs font-semibold text-slate-700">WalkWise Path</span>
                </div>
                <div className="flex items-center gap-3 pt-1">
                  <div className="w-24 h-2 rounded-full bg-gradient-to-r from-red-500 via-yellow-400 to-emerald-500" />
                  <span className="text-[10px] font-bold uppercase text-slate-400">0 to 100 score</span>
                </div>
              </div>
            </div>
          </div>

          {(loading || walkabilityLoading) && (
            <div className="absolute inset-0 bg-white/40 z-[500] flex items-center justify-center">
              <div className="bg-white rounded-xl shadow-xl p-5 flex items-center gap-3">
                <span className="material-symbols-outlined text-primary text-2xl animate-spin">refresh</span>
                <div>
                  <p className="font-bold text-slate-800">Preparing walk map...</p>
                  <p className="text-xs text-slate-500">Fetching walkability and path data</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
