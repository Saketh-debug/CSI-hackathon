import { useState, useEffect } from 'react'
import { MapContainer, ImageOverlay, Polyline, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { useRoute, useTemperatureData, useCanopyData } from '../api/hooks'
import MapResizer from '../components/MapResizer'

// ─────────────────────────────────────────────
// Fits the map to the route bounds on update
// ─────────────────────────────────────────────
function RouteFitter({ result }) {
  const map = useMap()

  useEffect(() => {
    if (result && result.fastest?.coords?.length) {
      const allCoords = [
        ...result.fastest.coords,
        ...(result.coolest && !result.routes_identical ? result.coolest.coords : []),
      ]
      if (allCoords.length > 0) {
        let minLat = Infinity, minLon = Infinity
        let maxLat = -Infinity, maxLon = -Infinity
        allCoords.forEach(([lat, lon]) => {
          if (lat < minLat) minLat = lat
          if (lat > maxLat) maxLat = lat
          if (lon < minLon) minLon = lon
          if (lon > maxLon) maxLon = lon
        })
        map.fitBounds([[minLat, minLon], [maxLat, maxLon]], { padding: [60, 60] })
      }
    }
  }, [result, map])

  return null
}

// ─────────────────────────────────────────────
// Bottom-sheet panel heights (vh)
// ─────────────────────────────────────────────
const SHEET_PEEK = '15vh'   // collapsed — just the drag handle + title
const SHEET_HALF = '55vh'   // half open
const SHEET_FULL = '88vh'   // fully open

export default function MobileCoolPathRouter() {
  const [origin, setOrigin] = useState('Madhapur, Hyderabad')
  const [destination, setDestination] = useState('Banjara Hills, Hyderabad')
  const [shadeWeight, setShadeWeight] = useState(0.5)
  const [tempWeight, setTempWeight] = useState(0.3)
  const [maxDev, setMaxDev] = useState(1.3)

  const [activeLayer, setActiveLayer] = useState('heatmap')
  const [mapStyle, setMapStyle] = useState('osm')

  // Bottom sheet state: 'peek' | 'half' | 'full'
  const [sheetState, setSheetState] = useState('half')

  const { result, loading, error, compute } = useRoute()
  const { data: tempData } = useTemperatureData()
  const { data: ndviData } = useCanopyData()

  const CENTER = [17.4474, 78.3762]
  const lstBounds = tempData?.bounds ?? [[17.0, 77.9], [17.9, 78.8]]
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
    setSheetState('half')
  }

  function handleSwap() {
    setOrigin(destination)
    setDestination(origin)
  }

  const mapCenter = fast?.coords?.length
    ? [
      (fast.coords[0][0] + fast.coords[fast.coords.length - 1][0]) / 2,
      (fast.coords[0][1] + fast.coords[fast.coords.length - 1][1]) / 2,
    ]
    : CENTER

  // Cycle through sheet heights on handle tap
  function cycleSheet() {
    setSheetState(prev =>
      prev === 'peek' ? 'half' :
        prev === 'half' ? 'full' : 'peek'
    )
  }

  // Sheet height map
  const sheetHeight = sheetState === 'peek' ? SHEET_PEEK :
    sheetState === 'half' ? SHEET_HALF : SHEET_FULL

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      display: 'flex',
      flexDirection: 'column',
      background: '#f8fafc',
      fontFamily: '"Inter", sans-serif',
      overflow: 'hidden',
    }}>
      {/* ── Minimal top bar ── */}
      <div style={{
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '12px 16px 10px',
        background: 'white',
        borderBottom: '1px solid #e2e8f0',
        flexShrink: 0,
      }}>
        <span className="material-symbols-outlined" style={{ color: '#10b77f', fontSize: '22px' }}>eco</span>
        <span style={{ fontWeight: 800, fontSize: '16px', color: '#0f172a', letterSpacing: '-0.3px' }}>
          CoolPath <span style={{ color: '#10b77f' }}>Mobile</span>
        </span>
        {/* Layer toggles in top bar */}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '6px' }}>
          <button
            onClick={() => setMapStyle(s => s === 'osm' ? 'satellite' : 'osm')}
            style={{
              background: '#f1f5f9',
              border: 'none',
              borderRadius: '8px',
              padding: '6px 8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px',
              fontWeight: 700,
              color: '#64748b',
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>
              {mapStyle === 'osm' ? 'satellite_alt' : 'map'}
            </span>
            {mapStyle === 'osm' ? 'SAT' : 'MAP'}
          </button>
          <button
            onClick={() => setActiveLayer(prev => prev === 'heatmap' ? null : 'heatmap')}
            style={{
              background: activeLayer === 'heatmap' ? '#fef2f2' : '#f1f5f9',
              border: activeLayer === 'heatmap' ? '1px solid #fca5a5' : '1px solid transparent',
              borderRadius: '8px',
              padding: '6px 8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px',
              fontWeight: 700,
              color: activeLayer === 'heatmap' ? '#ef4444' : '#64748b',
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>thermostat</span>
          </button>
          <button
            onClick={() => setActiveLayer(prev => prev === 'canopy' ? null : 'canopy')}
            style={{
              background: activeLayer === 'canopy' ? '#f0fdf4' : '#f1f5f9',
              border: activeLayer === 'canopy' ? '1px solid #86efac' : '1px solid transparent',
              borderRadius: '8px',
              padding: '6px 8px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '11px',
              fontWeight: 700,
              color: activeLayer === 'canopy' ? '#22c55e' : '#64748b',
            }}
          >
            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>park</span>
          </button>
        </div>
      </div>

      {/* ── Map — fills remaining space behind the sheet ── */}
      <div style={{ flex: 1, position: 'relative', zIndex: 0 }}>
        <MapContainer
          center={mapCenter}
          zoom={result ? 13 : 11}
          style={{ width: '100%', height: '100%', zIndex: 0 }}
          attributionControl={false}
          zoomControl={false}
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

          {activeLayer === 'heatmap' && tempData?.image_url && (
            <ImageOverlay url={tempData.image_url} bounds={lstBounds} opacity={0.35} />
          )}
          {activeLayer === 'canopy' && ndviData?.image_url && (
            <ImageOverlay url={ndviData.image_url} bounds={ndviBounds} opacity={0.30} />
          )}

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

        {/* Legend — bottom-left of map, above the sheet */}
        {result && (
          <div style={{
            position: 'absolute',
            bottom: `calc(${sheetHeight} + 12px)`,
            left: '12px',
            zIndex: 400,
            background: 'rgba(255,255,255,0.92)',
            backdropFilter: 'blur(8px)',
            borderRadius: '10px',
            border: '1px solid #e2e8f0',
            padding: '8px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '5px',
            transition: 'bottom 0.35s cubic-bezier(.4,0,.2,1)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '20px', height: '3px', background: '#10b77f', borderRadius: '2px' }} />
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#334155' }}>CoolPath</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '20px', borderTop: '2px dashed #ef4444' }} />
              <span style={{ fontSize: '11px', fontWeight: 600, color: '#334155' }}>Fastest</span>
            </div>
          </div>
        )}

        {/* Loading overlay on map */}
        {loading && (
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(255,255,255,0.5)',
            zIndex: 500,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <div style={{
              background: 'white',
              borderRadius: '16px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
              padding: '18px 24px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
            }}>
              <span className="material-symbols-outlined animate-spin" style={{ color: '#10b77f', fontSize: '26px' }}>refresh</span>
              <div>
                <p style={{ fontWeight: 700, fontSize: '14px', color: '#0f172a', margin: 0 }}>Computing routes…</p>
                <p style={{ fontSize: '11px', color: '#94a3b8', margin: '2px 0 0' }}>Climate-aware routing</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Bottom Sheet ── */}
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: sheetHeight,
        zIndex: 600,
        background: 'white',
        borderRadius: '20px 20px 0 0',
        boxShadow: '0 -4px 30px rgba(0,0,0,0.12)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        transition: 'height 0.35s cubic-bezier(.4,0,.2,1)',
      }}>
        {/* Drag Handle */}
        <div
          onClick={cycleSheet}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            paddingTop: '10px',
            paddingBottom: '6px',
            cursor: 'pointer',
            flexShrink: 0,
          }}
        >
          <div style={{
            width: '36px',
            height: '4px',
            background: '#cbd5e1',
            borderRadius: '2px',
            marginBottom: '8px',
          }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span className="material-symbols-outlined" style={{ color: '#10b77f', fontSize: '18px' }}>travel_explore</span>
            <span style={{ fontWeight: 700, fontSize: '13px', color: '#0f172a' }}>Plan Your CoolPath</span>
            <span className="material-symbols-outlined" style={{ color: '#94a3b8', fontSize: '16px', marginLeft: '4px' }}>
              {sheetState === 'full' ? 'expand_more' : 'expand_less'}
            </span>
          </div>
        </div>

        {/* Scrollable content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 16px 24px' }}>

          {/* Origin / Destination inputs */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '4px', marginLeft: '2px' }}>
                Origin
              </label>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                background: '#f8fafc',
                border: '1.5px solid #e2e8f0',
                borderRadius: '12px',
                padding: '0 12px',
              }}>
                <span className="material-symbols-outlined" style={{ color: '#94a3b8', fontSize: '18px', marginRight: '8px' }}>my_location</span>
                <input
                  style={{
                    flex: 1, border: 'none', background: 'transparent', fontSize: '14px',
                    color: '#334155', padding: '11px 0', outline: 'none',
                  }}
                  placeholder="Enter starting point"
                  value={origin}
                  onChange={e => setOrigin(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '10px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '4px', marginLeft: '2px' }}>
                Destination
              </label>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                background: '#f8fafc',
                border: '1.5px solid #e2e8f0',
                borderRadius: '12px',
                padding: '0 12px',
              }}>
                <span className="material-symbols-outlined" style={{ color: '#94a3b8', fontSize: '18px', marginRight: '8px' }}>location_on</span>
                <input
                  style={{
                    flex: 1, border: 'none', background: 'transparent', fontSize: '14px',
                    color: '#334155', padding: '11px 0', outline: 'none',
                  }}
                  placeholder="Enter destination"
                  value={destination}
                  onChange={e => setDestination(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
            <button
              onClick={handleCompute}
              disabled={loading}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                background: '#10b77f',
                color: 'white',
                border: 'none',
                borderRadius: '14px',
                padding: '13px',
                fontWeight: 700,
                fontSize: '14px',
                cursor: loading ? 'wait' : 'pointer',
                opacity: loading ? 0.65 : 1,
                boxShadow: '0 4px 14px rgba(16,183,127,0.25)',
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>
                {loading ? 'refresh' : 'directions'}
              </span>
              {loading ? 'Computing…' : 'Calculate Route'}
            </button>
            <button
              onClick={handleSwap}
              style={{
                width: '48px', height: '48px',
                background: '#f1f5f9',
                color: '#64748b',
                border: 'none',
                borderRadius: '14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
              }}
              title="Swap origin/destination"
            >
              <span className="material-symbols-outlined">swap_vert</span>
            </button>
          </div>

          {/* Error */}
          {error && (
            <div style={{
              background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '10px',
              padding: '10px 12px', marginBottom: '14px',
              display: 'flex', alignItems: 'flex-start', gap: '8px',
            }}>
              <span className="material-symbols-outlined" style={{ color: '#ef4444', fontSize: '16px', marginTop: '1px' }}>error</span>
              <span style={{ fontSize: '12px', color: '#b91c1c' }}>{error}</span>
            </div>
          )}

          {/* Routing Weights */}
          <div style={{
            background: '#f8fafc',
            borderRadius: '14px',
            padding: '12px 14px',
            marginBottom: '16px',
            border: '1px solid #e2e8f0',
          }}>
            <p style={{ fontSize: '10px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.07em', margin: '0 0 10px' }}>
              Routing Weights
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {[
                { label: '🌳 Shade importance', value: shadeWeight, set: setShadeWeight, min: 0, max: 1, step: 0.05, fmt: v => v.toFixed(2) },
                { label: '🌡️ Temp avoidance', value: tempWeight, set: setTempWeight, min: 0, max: 1, step: 0.05, fmt: v => v.toFixed(2) },
                { label: '📐 Max deviation', value: maxDev, set: setMaxDev, min: 1, max: 2, step: 0.1, fmt: v => v.toFixed(1) + '×' },
              ].map(({ label, value, set, min, max, step, fmt }) => (
                <div key={label}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                    <span style={{ fontSize: '12px', color: '#475569', fontWeight: 500 }}>{label}</span>
                    <span style={{ fontSize: '12px', fontWeight: 700, color: '#10b77f' }}>{fmt(value)}</span>
                  </div>
                  <input
                    type="range" min={min} max={max} step={step} value={value}
                    onChange={e => set(parseFloat(e.target.value))}
                    style={{ width: '100%', accentColor: '#10b77f' }}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Route Comparison */}
          {result && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                <p style={{ fontSize: '10px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.07em', margin: 0 }}>
                  Route Comparison
                </p>
                {!result.routes_identical && (
                  <span style={{
                    background: '#f0fdf4', color: '#16a34a', fontSize: '10px', fontWeight: 700,
                    padding: '2px 8px', borderRadius: '6px',
                  }}>Optimized for shade</span>
                )}
              </div>

              {/* Route cards — side by side on mobile */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '12px' }}>
                {/* Fastest */}
                <div style={{
                  background: 'white', border: '1.5px solid #e2e8f0', borderRadius: '14px',
                  padding: '12px',
                }}>
                  <span style={{
                    display: 'inline-block', background: '#fef2f2', color: '#ef4444',
                    fontSize: '9px', fontWeight: 700, padding: '2px 6px',
                    borderRadius: '5px', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px',
                  }}>Fastest</span>
                  <p style={{ fontSize: '18px', fontWeight: 800, color: '#0f172a', margin: '0 0 8px', display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                    {fast.distance_km} km
                    {fast.duration_min && <span style={{ fontSize: '12px', fontWeight: 600, color: '#94a3b8' }}>• {formatTime(fast.duration_min)}</span>}
                  </p>
                  <div style={{ marginBottom: '4px' }}>
                    <span style={{ fontSize: '9px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>Shade</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                      <div style={{ flex: 1, height: '4px', background: '#fee2e2', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', background: '#ef4444', width: `${fast.stats.shade_pct}%`, borderRadius: '2px' }} />
                      </div>
                      <span style={{ fontSize: '10px', fontWeight: 700, color: '#64748b' }}>{fast.stats.shade_pct}%</span>
                    </div>
                  </div>
                  <div>
                    <span style={{ fontSize: '9px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>Heat</span>
                    <div style={{ marginTop: '2px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, color: '#ef4444' }}>
                        {fast.stats.avg_temp_score > 0.66 ? 'High' : fast.stats.avg_temp_score > 0.33 ? 'Med' : 'Low'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* CoolPath */}
                <div style={{
                  background: '#f0fdf9', border: '2px solid #10b77f', borderRadius: '14px',
                  padding: '12px', boxShadow: '0 4px 12px rgba(16,183,127,0.12)',
                }}>
                  <span style={{
                    display: 'inline-block', background: '#10b77f', color: 'white',
                    fontSize: '9px', fontWeight: 700, padding: '2px 6px',
                    borderRadius: '5px', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px',
                  }}>CoolPath</span>
                  <p style={{ fontSize: '18px', fontWeight: 800, color: '#065f46', margin: '0 0 8px', display: 'flex', alignItems: 'baseline', gap: '6px' }}>
                    {cool.distance_km} km
                    {cool.duration_min && <span style={{ fontSize: '12px', fontWeight: 600, color: '#34d399' }}>• {formatTime(cool.duration_min)}</span>}
                  </p>
                  <div style={{ marginBottom: '4px' }}>
                    <span style={{ fontSize: '9px', color: '#6ee7b7', textTransform: 'uppercase', fontWeight: 700 }}>Shade</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
                      <div style={{ flex: 1, height: '4px', background: '#d1fae5', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', background: '#10b77f', width: `${cool.stats.shade_pct}%`, borderRadius: '2px' }} />
                      </div>
                      <span style={{ fontSize: '10px', fontWeight: 700, color: '#065f46' }}>{cool.stats.shade_pct}%</span>
                    </div>
                  </div>
                  <div>
                    <span style={{ fontSize: '9px', color: '#6ee7b7', textTransform: 'uppercase', fontWeight: 700 }}>Heat</span>
                    <div style={{ marginTop: '2px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, color: '#10b77f' }}>
                        {cool.stats.avg_temp_score > 0.66 ? 'High' : cool.stats.avg_temp_score > 0.33 ? 'Med' : 'Low'}
                      </span>
                    </div>
                  </div>
                  {!result.routes_identical && (
                    <div style={{ borderTop: '1px solid #a7f3d0', marginTop: '8px', paddingTop: '6px' }}>
                      <span style={{ fontSize: '9px', color: '#6ee7b7', fontWeight: 700 }}>
                        +{cool.deviation_pct}% extra dist.
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Insight */}
              <div style={{
                background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '12px',
                padding: '10px 12px',
              }}>
                <p style={{ fontSize: '12px', color: '#64748b', lineHeight: 1.5, margin: 0, fontStyle: 'italic' }}>
                  {result.routes_identical
                    ? <><span style={{ fontWeight: 700, color: '#10b77f' }}>Note:</span> Both routes are identical — the fastest path already has good shade coverage.</>
                    : <><span style={{ fontWeight: 700, color: '#10b77f' }}>CoolPath:</span> {cool.stats.shade_pct - fast.stats.shade_pct > 0
                      ? `Gives ${(cool.stats.shade_pct - fast.stats.shade_pct).toFixed(0)}% more shade with only +${cool.deviation_pct}% extra distance.`
                      : `Avoids hotter zones while staying close to the fastest path.`}</>
                  }
                </p>
              </div>
            </div>
          )}

          {/* Empty state */}
          {!result && !loading && (
            <div style={{ textAlign: 'center', padding: '16px 0 8px', color: '#94a3b8' }}>
              <span className="material-symbols-outlined" style={{ fontSize: '36px', display: 'block', marginBottom: '6px' }}>route</span>
              <p style={{ fontSize: '13px', margin: 0 }}>Enter locations above and tap Calculate Route.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
