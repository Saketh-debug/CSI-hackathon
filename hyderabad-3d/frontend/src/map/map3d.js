/**
 * Map3D — MapLibre GL map initialisation
 * =========================================
 * - Loads 3D buildings from /buildings GeoJSON
 * - Loads roads from /roads GeoJSON
 * - Sets up layer toggles
 * - Exposes addRoute() for the routing module
 *
 * Upgrade path:
 *   - Replace GeoJSON sources with PMTiles for full city coverage
 *   - Add deck.gl layers for heat/shadow overlays
 */

import maplibregl from 'maplibre-gl'
import { BACKEND_URL, ROAD_COLORS, BUILDING_COLOR, BUILDING_BASE_HEIGHT } from '../config.js'

// Centre on HITEC City / Madhapur
const CENTER = [78.3762, 17.4474]   // [lon, lat]
const ZOOM   = 15
const PITCH  = 50    // degrees tilt
const BEARING = -15  // slight rotation for drama

/**
 * Initialise the MapLibre map and load all data layers.
 * @param {string} containerId  — DOM element id
 * @returns {Promise<maplibregl.Map>}
 */
export async function initMap(containerId) {
  const map = new maplibregl.Map({
    container: containerId,
    style: {
      version: 8,
      glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
      sources: {
        // Base raster tiles from OpenStreetMap (no API key needed)
        'osm-raster': {
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          attribution: '© OpenStreetMap contributors',
          maxzoom: 19,
        },
      },
      layers: [
        {
          id: 'background',
          type: 'background',
          paint: { 'background-color': '#0f172a' },
        },
        {
          id: 'osm-tiles',
          type: 'raster',
          source: 'osm-raster',
          paint: {
            'raster-opacity': 0.35,   // dim the raster — 3D geometry is the star
            'raster-saturation': -0.5,
          },
        },
      ],
    },
    center: CENTER,
    zoom: ZOOM,
    pitch: PITCH,
    bearing: BEARING,
    antialias: true,
  })

  // Navigation controls (zoom, compass, pitch)
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'bottom-right')

  // Scale bar
  map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left')

  await new Promise(resolve => map.on('load', resolve))

  // ── Load data layers ──
  await Promise.all([
    loadBuildingLayer(map),
    loadRoadLayers(map),
  ])

  // ── Hide loading overlay ──
  document.getElementById('map-loading')?.classList.add('hidden')

  // ── Layer toggle bindings ──
  setupLayerToggles(map)

  // ── Animated intro fly-in ──
  setTimeout(() => {
    map.easeTo({ center: CENTER, zoom: 15.2, pitch: 52, bearing: -10, duration: 2500 })
  }, 800)

  return map
}

// ── Buildings ────────────────────────────────────────────────────────────────

async function loadBuildingLayer(map) {
  setLoadingStatus('Fetching building footprints…')
  try {
    const res = await fetch(`${BACKEND_URL}/buildings`)
    if (!res.ok) throw new Error(`Buildings: HTTP ${res.status}`)
    const geojson = await res.json()

    map.addSource('buildings', { type: 'geojson', data: geojson })

    // Ground shadow / base
    map.addLayer({
      id: 'buildings-shadow',
      type: 'fill-extrusion',
      source: 'buildings',
      paint: {
        'fill-extrusion-color': '#0f172a',
        'fill-extrusion-height': ['get', 'height'],
        'fill-extrusion-base': 0,
        'fill-extrusion-opacity': 0.4,
        'fill-extrusion-translate': [2, 2],
      },
    })

    // Main building extrusion
    map.addLayer({
      id: 'buildings-3d',
      type: 'fill-extrusion',
      source: 'buildings',
      paint: {
        // Height-based colour gradient: short=dark slate, tall=cyan accent
        'fill-extrusion-color': [
          'interpolate', ['linear'], ['get', 'height'],
          0,   '#1e293b',
          10,  '#334155',
          20,  '#475569',
          40,  '#0e7490',
          80,  '#0891b2',
          150, '#22d3ee',
        ],
        'fill-extrusion-height': ['get', 'height'],
        'fill-extrusion-base': 0,
        'fill-extrusion-opacity': 0.9,
        'fill-extrusion-ambient-occlusion-intensity': 0.4,
        'fill-extrusion-ambient-occlusion-radius': 3,
      },
    })

    console.log(`[map] Buildings loaded: ${geojson.features.length} polygons`)
  } catch (err) {
    console.error('[map] Failed to load buildings:', err)
    setLoadingStatus('⚠️ Buildings unavailable (run precompute first)')
  }
}

// ── Roads ────────────────────────────────────────────────────────────────────

async function loadRoadLayers(map) {
  setLoadingStatus('Fetching road network…')
  try {
    const res = await fetch(`${BACKEND_URL}/roads`)
    if (!res.ok) throw new Error(`Roads: HTTP ${res.status}`)
    const geojson = await res.json()

    map.addSource('roads', { type: 'geojson', data: geojson })

    // Road casing (outline) — drawn first (below)
    map.addLayer({
      id: 'roads-casing',
      type: 'line',
      source: 'roads',
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': '#0f172a',
        'line-width': [
          'match', ['get', 'road_type'],
          ['motorway', 'trunk'], 9,
          ['primary', 'primary_link'], 7,
          ['secondary', 'secondary_link'], 5,
          3,
        ],
        'line-opacity': 0.8,
      },
    })

    // Road fill
    map.addLayer({
      id: 'roads-fill',
      type: 'line',
      source: 'roads',
      layout: {
        'line-join': 'round',
        'line-cap': 'round',
      },
      paint: {
        'line-color': [
          'match', ['get', 'road_type'],
          ['motorway', 'motorway_link'], '#f97316',
          ['trunk', 'trunk_link'],        '#fb923c',
          ['primary', 'primary_link'],    '#eab308',
          ['secondary', 'secondary_link'],'#94a3b8',
          ['tertiary', 'tertiary_link'],  '#64748b',
          '#475569',
        ],
        'line-width': [
          'match', ['get', 'road_type'],
          ['motorway', 'trunk'], 6,
          ['primary', 'primary_link'], 4,
          ['secondary', 'secondary_link'], 3,
          2,
        ],
        'line-opacity': 0.9,
      },
    })

    console.log(`[map] Roads loaded: ${geojson.features.length} segments`)
  } catch (err) {
    console.error('[map] Failed to load roads:', err)
    setLoadingStatus('⚠️ Roads unavailable (run precompute first)')
  }
}

// ── Route layer ───────────────────────────────────────────────────────────────

/**
 * Draw or update the route line on the map.
 * @param {maplibregl.Map} map
 * @param {Object} routeFeature — GeoJSON Feature with LineString geometry
 */
export function drawRoute(map, routeFeature) {
  // Remove existing route layers/sources
  clearRoute(map)

  const geojson = { type: 'FeatureCollection', features: [routeFeature] }

  // Glow outer
  map.addSource('route', { type: 'geojson', data: geojson })

  map.addLayer({
    id: 'route-glow',
    type: 'line',
    source: 'route',
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: {
      'line-color': '#22d3ee',
      'line-width': 14,
      'line-opacity': 0.25,
      'line-blur': 6,
    },
  })

  map.addLayer({
    id: 'route-line',
    type: 'line',
    source: 'route',
    layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: {
      'line-color': '#22d3ee',
      'line-width': 5,
      'line-opacity': 1.0,
    },
  })

  // Animated dot along route start/end markers
  const coords = routeFeature.geometry.coordinates
  if (coords.length > 0) {
    addMarker(map, coords[0],             '🟢', 'origin-marker')
    addMarker(map, coords[coords.length - 1], '🔴', 'dest-marker')
  }

  // Fit map to route
  if (coords.length > 1) {
    const lngs = coords.map(c => c[0])
    const lats  = coords.map(c => c[1])
    map.fitBounds(
      [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
      { padding: { top: 80, bottom: 80, left: 420, right: 60 }, duration: 1200, pitch: 45 }
    )
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

export function clearRoute(map) {
  ['route-glow', 'route-line'].forEach(id => {
    if (map.getLayer(id)) map.removeLayer(id)
  })
  if (map.getSource('route')) map.removeSource('route')

  // Remove old markers
  document.querySelectorAll('.route-marker').forEach(el => el.remove())
  if (window._routeMarkers) {
    window._routeMarkers.forEach(m => m.remove())
    window._routeMarkers = []
  }
}

function addMarker(map, coord, emoji, id) {
  const el = document.createElement('div')
  el.className = 'route-marker'
  el.textContent = emoji
  el.style.cssText = 'font-size:22px;cursor:pointer;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.6));'

  const marker = new maplibregl.Marker({ element: el })
    .setLngLat(coord)
    .addTo(map)

  window._routeMarkers = window._routeMarkers || []
  window._routeMarkers.push(marker)
}

function setLoadingStatus(msg) {
  const el = document.getElementById('loading-status')
  if (el) el.textContent = msg
}

// ── Layer toggles ──────────────────────────────────────────────────────────

function setupLayerToggles(map) {
  // Buildings toggle
  document.getElementById('toggle-buildings')?.addEventListener('change', e => {
    const vis = e.target.checked ? 'visible' : 'none'
    ;['buildings-3d', 'buildings-shadow'].forEach(id => {
      if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', vis)
    })
  })

  // Roads toggle
  document.getElementById('toggle-roads')?.addEventListener('change', e => {
    const vis = e.target.checked ? 'visible' : 'none'
    ;['roads-fill', 'roads-casing'].forEach(id => {
      if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', vis)
    })
  })

  // Pitch toggle (flat vs 3D)
  document.getElementById('toggle-pitch')?.addEventListener('change', e => {
    map.easeTo({ pitch: e.target.checked ? 50 : 0, duration: 800 })
  })
}
