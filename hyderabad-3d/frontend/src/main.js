/**
 * Hyderabad 3D City — Main Entry Point
 * Bootstraps the app: renders shell, initialises map, wires up UI.
 */

import './style.css'
import 'maplibre-gl/dist/maplibre-gl.css'

import { createAppShell } from './ui/shell.js'
import { initMap }        from './map/map3d.js'
import { initSearch }     from './ui/searchPanel.js'

// ── Render shell HTML into #app ──────────────────────────────────────────────
const appEl = document.getElementById('app')
if (appEl) appEl.innerHTML = createAppShell()

// ── Boot once DOM is ready ───────────────────────────────────────────────────
async function boot() {
  try {
    const map = await initMap('map-container')
    initSearch(map)
  } catch (err) {
    console.error('[boot] Fatal error:', err)
    const loading = document.getElementById('map-loading')
    if (loading) {
      loading.innerHTML = `
        <div style="text-align:center;color:#fca5a5;padding:40px">
          <div style="font-size:32px;margin-bottom:12px">⚠️</div>
          <div style="font-size:16px;font-weight:600">Failed to initialise map</div>
          <div style="font-size:13px;color:#94a3b8;margin-top:8px">${err.message}</div>
          <div style="font-size:12px;color:#64748b;margin-top:16px">
            Make sure the backend is running:<br/>
            <code style="color:#22d3ee">uvicorn main:app --reload</code>
          </div>
        </div>
      `
    }
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot)
} else {
  boot()
}
