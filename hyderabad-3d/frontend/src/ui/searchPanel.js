/**
 * Search Panel — wires up the route/geocode UI
 * =============================================
 * Handles:
 *   - "Find Route" button click
 *   - GPS location button
 *   - Calling backend /geocode + /route
 *   - Updating the result stat card
 *   - Error display
 */

import { drawRoute, clearRoute } from '../map/map3d.js'
import { BACKEND_URL } from '../config.js'

/**
 * Initialise search panel event listeners.
 * @param {maplibregl.Map} map
 */
export function initSearch(map) {
  const btnRoute  = document.getElementById('btn-route')
  const btnLocate = document.getElementById('btn-locate')

  btnRoute?.addEventListener('click', () => handleFindRoute(map))
  btnLocate?.addEventListener('click', () => handleGPS())

  // Allow Enter key in inputs
  ;['input-origin', 'input-dest'].forEach(id => {
    document.getElementById(id)?.addEventListener('keydown', e => {
      if (e.key === 'Enter') handleFindRoute(map)
    })
  })
}

// ── Route handler ─────────────────────────────────────────────────────────────

async function handleFindRoute(map) {
  const originText = document.getElementById('input-origin')?.value?.trim()
  const destText   = document.getElementById('input-dest')?.value?.trim()

  if (!originText || !destText) {
    showError('Please enter both origin and destination.')
    return
  }

  setLoading(true)
  hideError()
  hideRouteCard()

  try {
    // ── Step 1: Geocode both addresses ──
    setButtonText('Geocoding…')
    const [origin, dest] = await Promise.all([
      geocode(originText),
      geocode(destText),
    ])

    if (!origin) { showError(`Could not find: "${originText}"`); setLoading(false); return }
    if (!dest)   { showError(`Could not find: "${destText}"`);   setLoading(false); return }

    // ── Step 2: Fetch route ──
    setButtonText('Routing…')
    const params = new URLSearchParams({
      from_lat: origin.lat,
      from_lon: origin.lon,
      to_lat:   dest.lat,
      to_lon:   dest.lon,
    })

    const res = await fetch(`${BACKEND_URL}/route?${params}`)
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(body.detail || `HTTP ${res.status}`)
    }

    const routeFeature = await res.json()

    // ── Step 3: Draw on map ──
    drawRoute(map, routeFeature)

    // ── Step 4: Show stats ──
    const props = routeFeature.properties
    showRouteCard(props.distance_km, props.duration_min, props.node_count, props.query_time_ms)

  } catch (err) {
    console.error('[search] Route error:', err)
    showError(err.message || 'Routing failed. Is the backend running?')
    clearRoute(map)
  } finally {
    setLoading(false)
    setButtonText('Find Route')
  }
}

// ── GPS handler ───────────────────────────────────────────────────────────────

function handleGPS() {
  if (!navigator.geolocation) {
    showError('Geolocation not supported by your browser.')
    return
  }

  const btn = document.getElementById('btn-locate')
  if (btn) btn.textContent = '⏳'

  navigator.geolocation.getCurrentPosition(
    pos => {
      const { latitude, longitude } = pos.coords
      const originInput = document.getElementById('input-origin')
      if (originInput) originInput.value = `${latitude.toFixed(5)}, ${longitude.toFixed(5)}`
      if (btn) btn.textContent = '✅'
      setTimeout(() => { if (btn) btn.textContent = '📡' }, 2000)
    },
    err => {
      showError(`Location error: ${err.message}`)
      if (btn) btn.textContent = '📡'
    },
    { enableHighAccuracy: true, timeout: 8000 }
  )
}

// ── Geocode ───────────────────────────────────────────────────────────────────

async function geocode(query) {
  // If query is "lat, lon" format, parse directly
  const latLonMatch = query.match(/^(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)$/)
  if (latLonMatch) {
    return { lat: parseFloat(latLonMatch[1]), lon: parseFloat(latLonMatch[2]), name: query }
  }

  const res = await fetch(`${BACKEND_URL}/geocode?q=${encodeURIComponent(query)}`)
  if (!res.ok) return null
  return res.json()
}

// ── UI helpers ────────────────────────────────────────────────────────────────

function setLoading(loading) {
  const btn     = document.getElementById('btn-route')
  const spinner = document.getElementById('btn-route-spinner')
  if (btn)     btn.disabled = loading
  if (spinner) spinner.classList.toggle('hidden', !loading)
}

function setButtonText(text) {
  const el = document.getElementById('btn-route-text')
  if (el) el.textContent = text
}

function showError(msg) {
  const el = document.getElementById('error-msg')
  if (!el) return
  el.textContent = `⚠️ ${msg}`
  el.classList.remove('hidden')
}

function hideError() {
  document.getElementById('error-msg')?.classList.add('hidden')
}

function showRouteCard(distKm, durationMin, nodes, queryMs) {
  document.getElementById('stat-dist')?.textContent  && null
  document.getElementById('stat-dist').textContent   = distKm
  document.getElementById('stat-time').textContent   = durationMin
  document.getElementById('stat-nodes').textContent  = nodes
  document.getElementById('route-card')?.classList.remove('hidden')
}

function hideRouteCard() {
  document.getElementById('route-card')?.classList.add('hidden')
}
